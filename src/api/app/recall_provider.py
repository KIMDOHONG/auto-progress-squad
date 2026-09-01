from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse


OFFICIAL_RECALL_SOURCE_NAME = "자동차리콜센터"
OFFICIAL_RECALL_SOURCE_URL = "https://www.car.go.kr/home/main.do"
OFFICIAL_RECALL_HOSTS = frozenset({"car.go.kr", "www.car.go.kr"})


@dataclass(frozen=True, slots=True)
class RecallQuery:
    vehicle_id: str
    manufacturer: str
    model: str
    model_year: int
    project_code: str | None = None


@dataclass(frozen=True, slots=True)
class RecallRecord:
    recall_id: str
    title: str
    source_url: str
    published_at: str | None = None


class RecallProviderError(Exception):
    """The configured official provider could not complete a lookup."""


class RecallProvider(Protocol):
    source_name: str
    source_url: str

    def list_recalls(self, query: RecallQuery) -> Sequence[RecallRecord]: ...


def validate_official_recall_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_RECALL_HOSTS:
        raise RecallProviderError("recall source URL is not an approved official URL")
    return url


def validate_provider(provider: RecallProvider) -> None:
    if provider.source_name != OFFICIAL_RECALL_SOURCE_NAME:
        raise RecallProviderError("recall provider is not the approved official source")
    validate_official_recall_url(provider.source_url)


def validate_recall_records(records: Sequence[RecallRecord]) -> tuple[RecallRecord, ...]:
    validated: list[RecallRecord] = []
    seen_ids: set[str] = set()
    for record in records:
        if not record.recall_id.strip() or not record.title.strip():
            raise RecallProviderError("recall record requires an id and title")
        if record.recall_id in seen_ids:
            raise RecallProviderError("recall provider returned duplicate ids")
        validate_official_recall_url(record.source_url)
        seen_ids.add(record.recall_id)
        validated.append(record)
    return tuple(validated)
