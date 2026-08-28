from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .database import (
    fail_manual_ingestion,
    get_manual_ingestion_row,
    list_manual_chunk_rows,
    list_pending_manual_ingestion_rows,
    replace_manual_document,
)


MAX_MANUAL_BYTES = 100 * 1024 * 1024
MAX_CHUNK_CHARACTERS = 1_200
CHUNK_OVERLAP_CHARACTERS = 160
ALLOWED_MANUAL_HOSTS = {
    "hmc": "ownersmanual.hyundai.com",
    "kia": "ownersmanual.kia.com",
    "genesis": "ownersmanual.genesis.com",
}


class ManualIngestionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ManualManifestEntry:
    document_key: str
    document_name: str
    source_url: str
    file: str


@dataclass(frozen=True, slots=True)
class ManualIngestionResult:
    vehicle_id: str
    document_key: str
    status: str
    chunk_count: int = 0
    failure_code: str | None = None


def _validate_entry(raw_entry: object) -> ManualManifestEntry:
    if not isinstance(raw_entry, dict):
        raise ManualIngestionError(
            "manifest_invalid", "매뉴얼 manifest 항목 형식이 올바르지 않습니다."
        )
    required = ("document_key", "document_name", "source_url", "file")
    values = {key: raw_entry.get(key) for key in required}
    if not all(isinstance(value, str) and value.strip() for value in values.values()):
        raise ManualIngestionError(
            "manifest_invalid", "매뉴얼 manifest 필수 문자열을 확인해 주세요."
        )
    entry = ManualManifestEntry(**{key: str(value).strip() for key, value in values.items()})
    site_id = entry.document_key.partition(":")[0]
    expected_host = ALLOWED_MANUAL_HOSTS.get(site_id)
    parsed_url = urlsplit(entry.source_url)
    if (
        expected_host is None
        or parsed_url.scheme != "https"
        or parsed_url.hostname != expected_host
    ):
        raise ManualIngestionError(
            "manual_source_not_allowed",
            "공식 제조사 HTTPS 원문만 매뉴얼 출처로 등록할 수 있습니다.",
        )
    return entry


def load_manifest(source_root: Path) -> dict[str, ManualManifestEntry]:
    manifest_path = source_root / "manifest.json"
    if not manifest_path.is_file():
        raise ManualIngestionError(
            "manifest_not_found", "승인된 매뉴얼 manifest.json을 찾을 수 없습니다."
        )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ManualIngestionError(
            "manifest_invalid", "매뉴얼 manifest.json을 읽을 수 없습니다."
        ) from error
    entries = payload.get("documents") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        raise ManualIngestionError(
            "manifest_invalid", "manifest.json의 documents 목록을 확인해 주세요."
        )
    manifest: dict[str, ManualManifestEntry] = {}
    for raw_entry in entries:
        entry = _validate_entry(raw_entry)
        if entry.document_key in manifest:
            raise ManualIngestionError(
                "manifest_duplicate_document",
                "manifest.json에 같은 문서 키가 중복되어 있습니다.",
            )
        manifest[entry.document_key] = entry
    return manifest


def _resolve_source_file(source_root: Path, relative_file: str) -> Path:
    root = source_root.resolve()
    candidate = (root / relative_file).resolve()
    if not candidate.is_relative_to(root):
        raise ManualIngestionError(
            "manual_source_outside_root",
            "매뉴얼 파일은 승인된 소스 디렉터리 안에 있어야 합니다.",
        )
    if candidate.suffix.lower() not in {".pdf", ".txt"}:
        raise ManualIngestionError(
            "manual_format_not_supported", "PDF 또는 UTF-8 TXT 문서만 처리할 수 있습니다."
        )
    if not candidate.is_file():
        raise ManualIngestionError(
            "manual_file_not_found", "manifest에 등록된 매뉴얼 파일을 찾을 수 없습니다."
        )
    if candidate.stat().st_size > MAX_MANUAL_BYTES:
        raise ManualIngestionError(
            "manual_file_too_large", "매뉴얼 파일이 허용된 100MB를 초과했습니다."
        )
    return candidate


def _extract_pages(source_file: Path) -> list[tuple[int, str]]:
    if source_file.suffix.lower() == ".txt":
        try:
            text = source_file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ManualIngestionError(
                "manual_text_read_failed", "UTF-8 매뉴얼 텍스트를 읽을 수 없습니다."
            ) from error
        return [(1, text)]
    try:
        reader = PdfReader(source_file)
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise ManualIngestionError(
                "manual_pdf_encrypted", "암호화된 PDF는 자동 처리할 수 없습니다."
            )
        return [(index, page.extract_text() or "") for index, page in enumerate(reader.pages, 1)]
    except ManualIngestionError:
        raise
    except (OSError, PdfReadError) as error:
        raise ManualIngestionError(
            "manual_pdf_read_failed", "PDF 매뉴얼을 읽거나 텍스트를 추출할 수 없습니다."
        ) from error


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\r\n?", "\n", text)).strip()


def _chunk_page(page: int, text: str) -> list[dict[str, object]]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    chunks: list[dict[str, object]] = []
    start = 0
    while start < len(normalized):
        end = min(start + MAX_CHUNK_CHARACTERS, len(normalized))
        if end < len(normalized):
            boundary = max(
                normalized.rfind("\n", start + 400, end),
                normalized.rfind(". ", start + 400, end),
                normalized.rfind("다. ", start + 400, end),
            )
            if boundary > start:
                end = boundary + 1
        content = normalized[start:end].strip()
        if content:
            chunks.append({"page": page, "section": None, "content": content})
        if end >= len(normalized):
            break
        start = max(end - CHUNK_OVERLAP_CHARACTERS, start + 1)
    return chunks


def _extract_chunks(source_file: Path) -> tuple[list[dict[str, object]], int]:
    pages = _extract_pages(source_file)
    chunks = [chunk for page, text in pages for chunk in _chunk_page(page, text)]
    if not chunks:
        raise ManualIngestionError(
            "manual_text_empty", "매뉴얼에서 검색 가능한 텍스트를 추출하지 못했습니다."
        )
    return chunks, len(pages)


def ingest_vehicle_manual(
    database_path: Path, source_root: Path, vehicle_id: str
) -> ManualIngestionResult:
    job = get_manual_ingestion_row(database_path, vehicle_id)
    if job is None:
        raise ManualIngestionError(
            "verified_manual_required", "검증된 공식 매뉴얼이 등록된 차량이 필요합니다."
        )
    document_key = str(job["document_key"])
    try:
        manifest = load_manifest(source_root)
        entry = manifest.get(document_key)
        if entry is None:
            raise ManualIngestionError(
                "manifest_entry_missing", "현재 차량의 문서 키가 manifest에 없습니다."
            )
        source_file = _resolve_source_file(source_root, entry.file)
        chunks, page_count = _extract_chunks(source_file)
        try:
            content_sha256 = hashlib.sha256(source_file.read_bytes()).hexdigest()
        except OSError as error:
            raise ManualIngestionError(
                "manual_file_read_failed", "매뉴얼 파일을 다시 읽을 수 없습니다."
            ) from error
        replace_manual_document(
            database_path,
            vehicle_id=vehicle_id,
            document_key=document_key,
            document_name=entry.document_name,
            source_url=entry.source_url,
            content_sha256=content_sha256,
            page_count=page_count,
            chunks=chunks,
        )
        return ManualIngestionResult(
            vehicle_id=vehicle_id,
            document_key=document_key,
            status="ready",
            chunk_count=len(chunks),
        )
    except ManualIngestionError as error:
        fail_manual_ingestion(
            database_path,
            vehicle_id=vehicle_id,
            failure_code=error.code,
            failure_message=error.message,
        )
        return ManualIngestionResult(
            vehicle_id=vehicle_id,
            document_key=document_key,
            status="failed",
            failure_code=error.code,
        )


def run_pending_ingestion(
    database_path: Path, source_root: Path, vehicle_id: str | None = None
) -> list[ManualIngestionResult]:
    results: list[ManualIngestionResult] = []
    for pending in list_pending_manual_ingestion_rows(database_path, vehicle_id):
        current = get_manual_ingestion_row(database_path, str(pending["vehicle_id"]))
        if current is None or current["status"] != "pending":
            continue
        results.append(
            ingest_vehicle_manual(database_path, source_root, str(pending["vehicle_id"]))
        )
    return results


def _search_terms(question: str) -> list[str]:
    suffixes = ("에서", "으로", "까지", "부터", "에게", "은", "는", "이", "가", "을", "를", "의")
    terms: list[str] = []
    for raw_term in re.findall(r"[0-9a-zA-Z가-힣]{2,}", question.lower()):
        term = raw_term
        for suffix in suffixes:
            if term.endswith(suffix) and len(term) > len(suffix) + 1:
                term = term[: -len(suffix)]
                break
        if term not in terms:
            terms.append(term)
    return terms


def search_manual_document(
    database_path: Path, document_key: str, question: str, limit: int
) -> list[dict[str, object]]:
    terms = _search_terms(question)
    if not terms:
        return []
    ranked: list[tuple[int, int, dict[str, object]]] = []
    for index, row in enumerate(list_manual_chunk_rows(database_path, document_key)):
        content = str(row["content"])
        lowered = content.lower()
        score = sum(lowered.count(term) * max(len(term), 2) for term in terms)
        if score <= 0:
            continue
        ranked.append(
            (
                score,
                -index,
                {
                    "document_name": row["document_name"],
                    "source_url": row["source_url"],
                    "page": row["page"],
                    "section": row["section"],
                    "excerpt": content[:500],
                },
            )
        )
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in ranked[:limit]]
