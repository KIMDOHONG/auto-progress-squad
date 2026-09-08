from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen

from .config import Settings
from .database import (
    VehicleNotFoundError,
    get_manual_ingestion_row,
    get_vehicle_row,
    initialize_database,
    list_vehicle_rows,
)
from .manual_ingestion import MAX_MANUAL_BYTES, ingest_vehicle_manual


SUPPORTED_SITES = {
    "hmc": "ownersmanual.hyundai.com",
    "kia": "ownersmanual.kia.com",
    "genesis": "ownersmanual.genesis.com",
}
MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_HTML_BYTES = 5 * 1024 * 1024
MAX_WEBHELP_TOPICS = 1000
Fetch = Callable[[str, int], "FetchedResource"]


class OfficialManualPreparationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class FetchedResource:
    final_url: str
    content: bytes
    content_type: str = ""


@dataclass(frozen=True, slots=True)
class PreparedManual:
    vehicle_id: str
    document_key: str
    document_name: str
    source_kind: str
    source_count: int
    chunk_count: int


class _TocParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a" or self._href is not None:
            return
        values = dict(attrs)
        href = values.get("href")
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._text)))
            self._href = None
            self._text = []


class _TopicParser(HTMLParser):
    BLOCK_TAGS = {"br", "div", "h1", "h2", "h3", "h4", "li", "p", "table", "tr"}
    SKIP_TAGS = {"script", "style", "nav", "header", "footer"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capture_depth = 0
        self._skip_depth = 0
        self._heading_depth = 0
        self._heading_text: list[str] = []
        self._text: list[str] = []
        self.title: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "div" and "topic-contents" in classes and self._capture_depth == 0:
            self._capture_depth = 1
        elif self._capture_depth and tag == "div":
            self._capture_depth += 1
        if self._capture_depth and tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if self._capture_depth and not self._skip_depth:
            if tag in self.BLOCK_TAGS:
                self._text.append("\n")
            if tag in {"h1", "h2", "h3"} and self.title is None:
                self._heading_depth = 1
                self._heading_text = []

    def handle_data(self, data: str) -> None:
        if not self._capture_depth or self._skip_depth:
            return
        self._text.append(data)
        if self._heading_depth:
            self._heading_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._capture_depth:
            return
        if self._skip_depth and tag in self.SKIP_TAGS:
            self._skip_depth -= 1
        elif not self._skip_depth:
            if tag in {"h1", "h2", "h3"} and self._heading_depth:
                self.title = _clean_inline_text(" ".join(self._heading_text)) or None
                self._heading_depth = 0
            if tag in self.BLOCK_TAGS:
                self._text.append("\n")
        if tag == "div":
            self._capture_depth -= 1

    def text(self) -> str:
        lines = [_clean_inline_text(line) for line in "".join(self._text).splitlines()]
        return "\n".join(line for line in lines if line)


class _TopicLinkParser(HTMLParser):
    """Collect links that are part of a topic body, excluding global navigation."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capture_depth = 0
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "div" and "topic-contents" in classes and self._capture_depth == 0:
            self._capture_depth = 1
        elif self._capture_depth and tag == "div":
            self._capture_depth += 1
        if self._capture_depth and tag == "a" and self._href is None:
            href = values.get("href")
            if href:
                self._href = href
                self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._text)))
            self._href = None
            self._text = []
        if self._capture_depth and tag == "div":
            self._capture_depth -= 1


def _clean_inline_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _validate_url(url: str, expected_host: str, *, prefix: str | None = None) -> None:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as error:
        raise OfficialManualPreparationError(
            "official_manual_url_invalid", "공식 설명서 URL 형식이 올바르지 않습니다."
        ) from error
    if (
        parsed.scheme != "https"
        or parsed.hostname != expected_host
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or (prefix is not None and not parsed.path.startswith(prefix))
    ):
        raise OfficialManualPreparationError(
            "official_manual_url_not_allowed",
            "선택한 제조사의 공식 HTTPS 설명서 주소만 준비할 수 있습니다.",
        )


def _fetch(url: str, limit: int) -> FetchedResource:
    request = Request(
        url,
        headers={
            "Accept": "application/json,text/html,application/pdf;q=0.9,*/*;q=0.1",
            "User-Agent": "AUTO-SQUAD-manual-preparer/1.0",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - URL is allowlisted
            content = response.read(limit + 1)
            if len(content) > limit:
                raise OfficialManualPreparationError(
                    "official_manual_too_large", "공식 설명서 응답이 허용 크기를 초과했습니다."
                )
            return FetchedResource(
                final_url=response.geturl(),
                content=content,
                content_type=response.headers.get_content_type(),
            )
    except OfficialManualPreparationError:
        raise
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise OfficialManualPreparationError(
            "official_manual_fetch_failed", "공식 설명서 서버에서 원문을 가져오지 못했습니다."
        ) from error


def _fetch_official(
    url: str,
    expected_host: str,
    limit: int,
    fetch: Fetch,
    *,
    prefix: str | None = None,
) -> FetchedResource:
    _validate_url(url, expected_host, prefix=prefix)
    resource = fetch(url, limit)
    _validate_url(resource.final_url, expected_host, prefix=prefix)
    return resource


def _load_json(resource: FetchedResource) -> Mapping[str, object]:
    try:
        payload = json.loads(resource.content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise OfficialManualPreparationError(
            "official_manual_metadata_invalid", "공식 설명서 메타데이터를 해석하지 못했습니다."
        ) from error
    if not isinstance(payload, dict):
        raise OfficialManualPreparationError(
            "official_manual_metadata_invalid", "공식 설명서 메타데이터 형식이 올바르지 않습니다."
        )
    return payload


def _topic_links(toc_url: str, html: str, expected_host: str) -> list[tuple[str, str]]:
    parser = _TocParser()
    parser.feed(html)
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    base_path = urlsplit(toc_url).path.rsplit("/", 1)[0] + "/topics/"
    for href, label in parser.links:
        absolute = urljoin(toc_url, href)
        parsed = urlsplit(absolute)
        if not parsed.path.startswith(base_path) or not parsed.path.endswith(".html"):
            continue
        clean_url = parsed._replace(query="", fragment="").geturl()
        _validate_url(clean_url, expected_host, prefix=base_path)
        if clean_url not in seen:
            seen.add(clean_url)
            links.append((clean_url, _clean_inline_text(label)))
    if not links:
        raise OfficialManualPreparationError(
            "official_manual_toc_empty", "공식 웹 설명서 목차에서 본문 링크를 찾지 못했습니다."
        )
    return links


def _nested_topic_links(
    topic_url: str,
    html: str,
    expected_host: str,
    topic_path_prefix: str,
) -> list[tuple[str, str]]:
    parser = _TopicLinkParser()
    parser.feed(html)
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    current_url = urlsplit(topic_url)._replace(query="", fragment="").geturl()
    for href, label in parser.links:
        absolute = urljoin(topic_url, href)
        parsed = urlsplit(absolute)
        if not parsed.path.startswith(topic_path_prefix) or not parsed.path.endswith(".html"):
            continue
        clean_url = parsed._replace(query="", fragment="").geturl()
        _validate_url(clean_url, expected_host, prefix=topic_path_prefix)
        if clean_url != current_url and clean_url not in seen:
            seen.add(clean_url)
            links.append((clean_url, _clean_inline_text(label)))
    return links


def _extract_topic(html: str, fallback_title: str) -> tuple[str, str]:
    parser = _TopicParser()
    parser.feed(html)
    content = parser.text()
    if not content:
        raise OfficialManualPreparationError(
            "official_manual_topic_empty", "공식 웹 설명서 페이지에서 본문을 찾지 못했습니다."
        )
    return parser.title or fallback_title or "설명서 본문", content


def _read_manifest(source_root: Path) -> dict[str, object]:
    manifest_path = source_root / "manifest.json"
    if not manifest_path.exists():
        return {"documents": []}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise OfficialManualPreparationError(
            "manifest_invalid", "기존 manifest.json을 읽을 수 없습니다."
        ) from error
    if not isinstance(payload, dict) or not isinstance(payload.get("documents"), list):
        raise OfficialManualPreparationError(
            "manifest_invalid", "기존 manifest.json의 documents 목록을 확인해 주세요."
        )
    return payload


def _upsert_manifest(source_root: Path, entry: dict[str, object]) -> None:
    source_root.mkdir(parents=True, exist_ok=True)
    payload = _read_manifest(source_root)
    documents = [
        item
        for item in payload["documents"]  # type: ignore[index]
        if not isinstance(item, dict) or item.get("document_key") != entry["document_key"]
    ]
    documents.append(entry)
    payload["documents"] = documents
    manifest_path = source_root / "manifest.json"
    temporary_path = source_root / "manifest.json.tmp"
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary_path.replace(manifest_path)


def _safe_part(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z_-]+", "-", value.strip()).strip("-")
    if not normalized:
        raise OfficialManualPreparationError(
            "official_manual_identity_invalid", "설명서 프로젝트 코드를 확인해 주세요."
        )
    return normalized


def prepare_vehicle_manual(
    database_path: Path,
    source_root: Path,
    vehicle_id: str,
    *,
    fetch: Fetch = _fetch,
) -> PreparedManual:
    try:
        vehicle = get_vehicle_row(database_path, vehicle_id)
    except VehicleNotFoundError as error:
        raise OfficialManualPreparationError(
            "vehicle_not_found", "등록된 차량을 찾을 수 없습니다."
        ) from error
    job = get_manual_ingestion_row(database_path, vehicle_id)
    site_id = str(vehicle["manual_site_id"] or "")
    expected_host = SUPPORTED_SITES.get(site_id)
    project_code = str(vehicle["manual_project_code"] or "")
    model_name = str(vehicle["manual_model_name"] or "")
    model_year = vehicle["manual_model_year"]
    if expected_host is None or not project_code or not model_name or model_year is None or job is None:
        raise OfficialManualPreparationError(
            "verified_hkg_manual_required",
            "현대·기아·제네시스 공식 설명서가 정확히 연결된 차량만 준비할 수 있습니다.",
        )

    base_url = f"https://{expected_host}"
    metadata_url = (
        f"{base_url}/api/v2/{site_id}/model/owners-manuals"
        f"?projectCode={quote(project_code, safe='')}&year={int(model_year)}"
        "&langCode=ko_KR&countryCode=A99"
    )
    metadata = _load_json(
        _fetch_official(metadata_url, expected_host, MAX_METADATA_BYTES, fetch)
    )
    owner_manual = metadata.get("omManual")
    if not isinstance(owner_manual, dict):
        raise OfficialManualPreparationError(
            "official_manual_not_found", "공식 사이트에 해당 차량의 취급설명서가 없습니다."
        )

    document_key = str(job["document_key"])
    document_name = f"{model_name} {int(model_year)} 취급설명서"
    relative_root = Path(site_id) / _safe_part(project_code) / str(int(model_year))
    destination_root = source_root / relative_root
    destination_root.mkdir(parents=True, exist_ok=True)
    source_url = str(job["source_url"])

    pdf_url = owner_manual.get("pdfManual")
    webhelp_toc = owner_manual.get("webhelpToc")
    webhelp_manual = owner_manual.get("webhelpManual")
    if isinstance(pdf_url, str) and pdf_url.strip():
        resource = _fetch_official(
            pdf_url.strip(), expected_host, MAX_MANUAL_BYTES, fetch, prefix="/full_pdf/"
        )
        if not resource.content.startswith(b"%PDF"):
            raise OfficialManualPreparationError(
                "official_manual_pdf_invalid", "공식 설명서 응답이 PDF 형식이 아닙니다."
            )
        relative_file = relative_root / "owners-manual.pdf"
        (source_root / relative_file).write_bytes(resource.content)
        entry: dict[str, object] = {
            "document_key": document_key,
            "document_name": document_name,
            "source_url": source_url,
            "file": relative_file.as_posix(),
        }
        source_kind = "pdf"
        source_count = 1
    else:
        toc_url = webhelp_toc if isinstance(webhelp_toc, str) else webhelp_manual
        if not isinstance(toc_url, str) or not toc_url.strip():
            raise OfficialManualPreparationError(
                "official_manual_not_found", "공식 사이트에 PDF 또는 웹 취급설명서가 없습니다."
            )
        toc_url = toc_url.strip()
        toc_resource = _fetch_official(
            toc_url, expected_host, MAX_HTML_BYTES, fetch, prefix="/full_webhelp/"
        )
        try:
            toc_html = toc_resource.content.decode("utf-8")
        except UnicodeError as error:
            raise OfficialManualPreparationError(
                "official_manual_html_invalid", "공식 웹 설명서 목차를 해석하지 못했습니다."
            ) from error
        chapters: list[dict[str, str]] = []
        topic_path_prefix = urlsplit(toc_resource.final_url).path.rsplit("/", 1)[0] + "/topics/"
        pending_topics = _topic_links(toc_resource.final_url, toc_html, expected_host)
        initial_topic_count = len(pending_topics)
        queued_urls = {url for url, _title in pending_topics}
        processed_urls: set[str] = set()
        next_topic = 0
        while next_topic < len(pending_topics):
            topic_url, toc_title = pending_topics[next_topic]
            next_topic += 1
            if topic_url in processed_urls:
                continue
            processed_urls.add(topic_url)
            try:
                topic_resource = _fetch_official(
                    topic_url,
                    expected_host,
                    MAX_HTML_BYTES,
                    fetch,
                    prefix="/full_webhelp/",
                )
            except OfficialManualPreparationError as error:
                # Some official landing pages contain stale links to removed
                # subtopics. A missing optional child must not discard the
                # complete manual, while every TOC entry remains mandatory.
                if (
                    next_topic > initial_topic_count
                    and error.code == "official_manual_fetch_failed"
                ):
                    continue
                raise
            try:
                topic_html = topic_resource.content.decode("utf-8")
            except UnicodeError as error:
                raise OfficialManualPreparationError(
                    "official_manual_html_invalid", "공식 웹 설명서 본문을 해석하지 못했습니다."
                ) from error
            title, content = _extract_topic(topic_html, toc_title)
            for nested_url, nested_title in _nested_topic_links(
                topic_resource.final_url,
                topic_html,
                expected_host,
                topic_path_prefix,
            ):
                if nested_url in queued_urls:
                    continue
                if len(queued_urls) >= MAX_WEBHELP_TOPICS:
                    raise OfficialManualPreparationError(
                        "official_manual_topic_limit_exceeded",
                        "공식 웹 설명서의 본문 페이지 수가 허용 범위를 초과했습니다.",
                    )
                queued_urls.add(nested_url)
                pending_topics.append((nested_url, nested_title))
            index = len(chapters) + 1
            filename = f"{index:03d}-{Path(urlsplit(topic_url).path).stem}.txt"
            relative_file = relative_root / "topics" / filename
            file_path = source_root / relative_file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f"{title}\n\n{content}\n", encoding="utf-8")
            chapters.append(
                {
                    "title": title,
                    "source_url": topic_resource.final_url,
                    "file": relative_file.as_posix(),
                }
            )
        entry = {
            "document_key": document_key,
            "document_name": document_name,
            "source_url": source_url,
            "chapters": chapters,
        }
        source_kind = "webhelp"
        source_count = len(chapters)

    _upsert_manifest(source_root, entry)
    ingestion = ingest_vehicle_manual(database_path, source_root, vehicle_id)
    if ingestion.status != "ready":
        raise OfficialManualPreparationError(
            ingestion.failure_code or "manual_ingestion_failed",
            "공식 원문은 준비했지만 검색 인덱스를 만들지 못했습니다.",
        )
    return PreparedManual(
        vehicle_id=vehicle_id,
        document_key=document_key,
        document_name=document_name,
        source_kind=source_kind,
        source_count=source_count,
        chunk_count=ingestion.chunk_count,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="등록된 현대·기아·제네시스 차량의 공식 설명서를 로컬 RAG 인덱스로 준비합니다."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--vehicle-id", help="준비할 등록 차량 ID")
    target.add_argument("--all", action="store_true", help="연결된 현대·기아·제네시스 차량 전체")
    parser.add_argument(
        "--confirm-official-source",
        action="store_true",
        help="공식 사이트 이용 조건을 확인하고 로컬 원문 준비를 승인함",
    )
    arguments = parser.parse_args()
    if not arguments.confirm_official_source:
        parser.error("원문을 저장하기 전에 --confirm-official-source가 필요합니다.")
    settings = Settings.from_env()
    initialize_database(settings.database_path)
    vehicle_ids = (
        [arguments.vehicle_id]
        if arguments.vehicle_id
        else [
            str(row["id"])
            for row in list_vehicle_rows(settings.database_path)
            if row["manual_site_id"] in SUPPORTED_SITES
        ]
    )
    results = [
        prepare_vehicle_manual(
            settings.database_path, settings.manual_source_dir, vehicle_id
        )
        for vehicle_id in vehicle_ids
    ]
    print(
        json.dumps(
            [
                {
                    "vehicle_id": result.vehicle_id,
                    "document_key": result.document_key,
                    "document_name": result.document_name,
                    "source_kind": result.source_kind,
                    "source_count": result.source_count,
                    "chunk_count": result.chunk_count,
                }
                for result in results
            ],
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
