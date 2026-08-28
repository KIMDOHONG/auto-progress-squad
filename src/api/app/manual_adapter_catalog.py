from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from .manual_adapters import ManufacturerAdapterId


CATALOG_FILE_NAME = "adapter-manifest.json"
CATALOG_MANUFACTURERS = {"chevrolet", "kgm"}
ALLOWED_CATALOG_HOSTS = {
    "chevrolet": "www.chevrolet.co.kr",
    "kgm": "www.kg-mobility.com",
}


class ManualAdapterCatalogError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        details: list[dict[str, object]] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ManualChapterLink:
    title: str
    url: str


@dataclass(frozen=True, slots=True)
class ManualCatalogEntry:
    manufacturer_id: ManufacturerAdapterId
    model: str
    model_year: int
    generation: str
    manual_title: str
    official_url: str
    source_checked_at: str
    chapters: tuple[ManualChapterLink, ...]


def _required_string(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManualAdapterCatalogError(
            "manual_adapter_catalog_invalid",
            f"adapter-manifest.json의 {key} 값을 확인해 주세요.",
        )
    return value.strip()


def _required_date(raw: dict[str, object], key: str) -> str:
    value = _required_string(raw, key)
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ManualAdapterCatalogError(
            "manual_adapter_catalog_invalid",
            f"adapter-manifest.json의 {key}는 YYYY-MM-DD 형식이어야 합니다.",
        ) from error
    return value


def _validate_official_url(
    manufacturer_id: str, url: str, *, require_pdf: bool = False
) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != ALLOWED_CATALOG_HOSTS[manufacturer_id]
        or (require_pdf and not parsed.path.lower().endswith(".pdf"))
    ):
        raise ManualAdapterCatalogError(
            "manual_adapter_source_not_allowed",
            "승인된 제조사 HTTPS 원문과 PDF만 매핑할 수 있습니다.",
        )


def _parse_entry(raw: object) -> ManualCatalogEntry:
    if not isinstance(raw, dict):
        raise ManualAdapterCatalogError(
            "manual_adapter_catalog_invalid",
            "adapter-manifest.json의 mappings 항목 형식을 확인해 주세요.",
        )

    manufacturer_id = _required_string(raw, "manufacturer_id")
    if manufacturer_id not in CATALOG_MANUFACTURERS:
        raise ManualAdapterCatalogError(
            "manual_adapter_catalog_invalid",
            "카탈로그 매핑은 쉐보레와 KGM만 지원합니다.",
        )

    model_year = raw.get("model_year")
    if not isinstance(model_year, int) or not 1990 <= model_year <= 2100:
        raise ManualAdapterCatalogError(
            "manual_adapter_catalog_invalid",
            "adapter-manifest.json의 model_year 값을 확인해 주세요.",
        )

    chapters_raw = raw.get("chapters")
    if not isinstance(chapters_raw, list) or not chapters_raw:
        raise ManualAdapterCatalogError(
            "manual_adapter_catalog_invalid",
            "각 매핑에는 한 개 이상의 공식 PDF 장이 필요합니다.",
        )

    chapters: list[ManualChapterLink] = []
    seen_urls: set[str] = set()
    for chapter_raw in chapters_raw:
        if not isinstance(chapter_raw, dict):
            raise ManualAdapterCatalogError(
                "manual_adapter_catalog_invalid",
                "chapters 항목 형식을 확인해 주세요.",
            )
        title = _required_string(chapter_raw, "title")
        url = _required_string(chapter_raw, "url")
        _validate_official_url(manufacturer_id, url, require_pdf=True)
        if url in seen_urls:
            raise ManualAdapterCatalogError(
                "manual_adapter_catalog_duplicate_chapter",
                "같은 PDF URL을 한 매핑에 중복 등록할 수 없습니다.",
            )
        seen_urls.add(url)
        chapters.append(ManualChapterLink(title=title, url=url))

    official_url = _required_string(raw, "official_url")
    _validate_official_url(manufacturer_id, official_url)
    return ManualCatalogEntry(
        manufacturer_id=cast(ManufacturerAdapterId, manufacturer_id),
        model=_required_string(raw, "model"),
        model_year=model_year,
        generation=_required_string(raw, "generation"),
        manual_title=_required_string(raw, "manual_title"),
        official_url=official_url,
        source_checked_at=_required_date(raw, "source_checked_at"),
        chapters=tuple(chapters),
    )


def load_manual_adapter_catalog(source_root: Path) -> tuple[ManualCatalogEntry, ...]:
    manifest_path = source_root / CATALOG_FILE_NAME
    if not manifest_path.is_file():
        raise ManualAdapterCatalogError(
            "manual_adapter_catalog_not_found",
            "관리자가 승인한 adapter-manifest.json을 찾을 수 없습니다.",
        )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ManualAdapterCatalogError(
            "manual_adapter_catalog_invalid",
            "adapter-manifest.json을 읽을 수 없습니다.",
        ) from error

    mappings = payload.get("mappings") if isinstance(payload, dict) else None
    if not isinstance(mappings, list):
        raise ManualAdapterCatalogError(
            "manual_adapter_catalog_invalid",
            "adapter-manifest.json의 mappings 목록을 확인해 주세요.",
        )

    entries = tuple(_parse_entry(mapping) for mapping in mappings)
    identities: set[tuple[str, str, int, str]] = set()
    for entry in entries:
        identity = (
            entry.manufacturer_id,
            entry.model.casefold(),
            entry.model_year,
            entry.generation.casefold(),
        )
        if identity in identities:
            raise ManualAdapterCatalogError(
                "manual_adapter_catalog_duplicate_mapping",
                "같은 제조사·차명·연식·세대 매핑이 중복되었습니다.",
            )
        identities.add(identity)
    return entries


def resolve_manual_catalog_entry(
    entries: tuple[ManualCatalogEntry, ...],
    *,
    manufacturer_id: str,
    model: str,
    model_year: int,
    generation: str | None,
) -> ManualCatalogEntry:
    if manufacturer_id not in CATALOG_MANUFACTURERS:
        raise ManualAdapterCatalogError(
            "manual_adapter_catalog_not_supported",
            "이 제조사는 승인 카탈로그 방식으로 조회하지 않습니다.",
        )

    matches = [
        entry
        for entry in entries
        if entry.manufacturer_id == manufacturer_id
        and entry.model.casefold() == model.strip().casefold()
        and entry.model_year == model_year
    ]
    if generation is not None:
        matches = [
            entry
            for entry in matches
            if entry.generation.casefold() == generation.strip().casefold()
        ]
    if not matches:
        raise ManualAdapterCatalogError(
            "manual_mapping_not_found",
            "정확히 일치하는 차명·연식·세대의 승인 매뉴얼이 없습니다.",
        )
    if len(matches) > 1:
        candidates = [
            {
                "generation": entry.generation,
                "manual_title": entry.manual_title,
                "source_checked_at": entry.source_checked_at,
            }
            for entry in sorted(matches, key=lambda item: item.generation.casefold())
        ]
        raise ManualAdapterCatalogError(
            "manual_generation_required",
            "같은 차명과 연식의 세대가 둘 이상이므로 세대를 선택해 주세요.",
            details=candidates,
        )
    return matches[0]
