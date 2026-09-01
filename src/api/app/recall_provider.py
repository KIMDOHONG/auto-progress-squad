from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse


OFFICIAL_RECALL_SOURCE_NAME = "자동차리콜센터"
OFFICIAL_RECALL_SOURCE_URL = "https://www.car.go.kr/home/main.do"
OFFICIAL_RECALL_HOSTS = frozenset({"car.go.kr", "www.car.go.kr"})


def _compact_recall_key_part(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


_MANUFACTURER_ALIASES = {
    "현대": "hyundai",
    "현대자동차": "hyundai",
    "hyundai": "hyundai",
    "hyundaimotorcompany": "hyundai",
    "기아": "kia",
    "기아자동차": "kia",
    "kia": "kia",
    "kiacorporation": "kia",
    "제네시스": "genesis",
    "genesis": "genesis",
    "bmw": "bmw",
    "bmw코리아": "bmw",
    "비엠더블유": "bmw",
    "비엠더블유코리아주": "bmw",
    "kgm": "kgm",
    "kg모빌리티": "kgm",
    "케이지모빌리티": "kgm",
    "쌍용자동차": "kgm",
    "chevrolet": "chevrolet",
    "쉐보레": "chevrolet",
    "한국gm": "chevrolet",
    "한국지엠": "chevrolet",
}


def normalize_recall_manufacturer(value: str) -> str:
    compact = _compact_recall_key_part(value)
    if not compact:
        raise ValueError("recall manufacturer must not be empty")
    return _MANUFACTURER_ALIASES.get(compact, compact)


def normalize_recall_key_part(value: str) -> str:
    compact = _compact_recall_key_part(value)
    if not compact:
        raise ValueError("recall key part must not be empty")
    return compact


def normalize_optional_recall_key_part(value: str | None) -> str | None:
    return normalize_recall_key_part(value) if value and value.strip() else None


@dataclass(frozen=True, slots=True)
class RecallVehicleKey:
    manufacturer: str
    model: str
    model_year: int
    generation: str | None = None
    project_code: str | None = None

    def __post_init__(self) -> None:
        if not 1990 <= self.model_year <= 2100:
            raise ValueError("recall model year is out of range")
        object.__setattr__(
            self, "manufacturer", normalize_recall_manufacturer(self.manufacturer)
        )
        object.__setattr__(self, "model", normalize_recall_key_part(self.model))
        object.__setattr__(
            self,
            "generation",
            normalize_optional_recall_key_part(self.generation),
        )
        object.__setattr__(
            self,
            "project_code",
            normalize_optional_recall_key_part(self.project_code),
        )

    @property
    def value(self) -> str:
        return "|".join(
            (
                self.manufacturer,
                self.model,
                str(self.model_year),
                self.generation or "-",
                self.project_code or "-",
            )
        )


@dataclass(frozen=True, slots=True)
class RecallQuery:
    vehicle_id: str
    manufacturer: str
    model: str
    model_year: int
    generation: str | None = None
    project_code: str | None = None

    @property
    def vehicle_key(self) -> RecallVehicleKey:
        return RecallVehicleKey(
            manufacturer=self.manufacturer,
            model=self.model,
            model_year=self.model_year,
            generation=self.generation,
            project_code=self.project_code,
        )


@dataclass(frozen=True, slots=True)
class RecallRecord:
    recall_id: str
    title: str
    source_url: str
    vehicle_key: RecallVehicleKey
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
    seen_identities: set[str] = set()
    for record in records:
        if not record.recall_id.strip() or not record.title.strip():
            raise RecallProviderError("recall record requires an id and title")
        if not isinstance(record.vehicle_key, RecallVehicleKey):
            raise RecallProviderError("recall record requires a normalized vehicle key")
        identity = f"{record.recall_id}:{record.vehicle_key.value}"
        if identity in seen_identities:
            raise RecallProviderError("recall provider returned duplicate ids")
        validate_official_recall_url(record.source_url)
        seen_identities.add(identity)
        validated.append(record)
    return tuple(validated)


def match_recall_records(
    vehicle_key: RecallVehicleKey, records: Sequence[RecallRecord]
) -> tuple[RecallRecord, ...]:
    return tuple(record for record in records if record.vehicle_key == vehicle_key)
