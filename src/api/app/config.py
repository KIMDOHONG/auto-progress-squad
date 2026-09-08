from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "https://kimdohong.github.io",
)
ManualSearchMode = Literal["keyword", "embedding", "hybrid"]
ManualAnswerMode = Literal["extractive", "source-list", "openvino"]


@dataclass(frozen=True, slots=True)
class Settings:
    database_path: Path
    cors_origins: tuple[str, ...]
    manual_source_dir: Path = PROJECT_DIR / "data" / "manuals"
    manual_search_mode: ManualSearchMode = "keyword"
    manual_embedding_model: str = "intfloat/multilingual-e5-small"
    manual_embedding_revision: str = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    manual_embedding_file: str = "openvino/openvino_model.xml"
    manual_embedding_min_score: float = 0.82
    manual_answer_mode: ManualAnswerMode = "extractive"
    manual_generation_model_path: Path | None = None
    manual_generation_device: str = "CPU"
    manual_generation_max_new_tokens: int = 160
    manual_grounding_min_token_overlap: float = 0.55
    naver_maps_client_id: str | None = None
    naver_maps_client_secret: str | None = None
    naver_maps_browser_client_id: str | None = None
    naver_maps_timeout_seconds: float = 5.0
    station_catalog_path: Path | None = None
    ev_charger_service_key: str | None = None
    ev_charger_timeout_seconds: float = 10.0
    ev_charger_cache_ttl_seconds: float = 1_800.0
    ev_charger_page_size: int = 9_999
    ev_charger_max_pages: int = 100
    ev_charger_region_codes: tuple[str, ...] = ()
    hydrogen_station_service_key: str | None = None
    hydrogen_station_timeout_seconds: float = 10.0
    hydrogen_station_cache_ttl_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.manual_search_mode not in {"keyword", "embedding", "hybrid"}:
            raise ValueError(
                "APS_MANUAL_SEARCH_MODE must be keyword, embedding, or hybrid"
            )
        if not 0 <= self.manual_embedding_min_score <= 1:
            raise ValueError("APS_MANUAL_EMBEDDING_MIN_SCORE must be between 0 and 1")
        if self.manual_answer_mode not in {"extractive", "source-list", "openvino"}:
            raise ValueError(
                "APS_MANUAL_ANSWER_MODE must be extractive, source-list, or openvino"
            )
        if not self.manual_generation_device.strip():
            raise ValueError("APS_MANUAL_GENERATION_DEVICE must not be empty")
        if self.manual_generation_max_new_tokens < 1:
            raise ValueError("APS_MANUAL_GENERATION_MAX_NEW_TOKENS must be at least 1")
        if not 0 <= self.manual_grounding_min_token_overlap <= 1:
            raise ValueError(
                "APS_MANUAL_GROUNDING_MIN_TOKEN_OVERLAP must be between 0 and 1"
            )
        if bool(self.naver_maps_client_id) != bool(self.naver_maps_client_secret):
            raise ValueError(
                "APS_NAVER_MAPS_CLIENT_ID and APS_NAVER_MAPS_CLIENT_SECRET must be set together"
            )
        if self.naver_maps_timeout_seconds <= 0:
            raise ValueError("APS_NAVER_MAPS_TIMEOUT_SECONDS must be greater than zero")
        if self.ev_charger_timeout_seconds <= 0:
            raise ValueError("APS_EV_CHARGER_TIMEOUT_SECONDS must be greater than zero")
        if self.ev_charger_cache_ttl_seconds < 0:
            raise ValueError("APS_EV_CHARGER_CACHE_TTL_SECONDS must not be negative")
        if not 10 <= self.ev_charger_page_size <= 9_999:
            raise ValueError("APS_EV_CHARGER_PAGE_SIZE must be between 10 and 9999")
        if self.ev_charger_max_pages < 1:
            raise ValueError("APS_EV_CHARGER_MAX_PAGES must be at least 1")
        if any(
            len(code) != 2 or not code.isdigit()
            for code in self.ev_charger_region_codes
        ):
            raise ValueError("APS_EV_CHARGER_REGION_CODES must contain two-digit codes")
        if self.hydrogen_station_timeout_seconds <= 0:
            raise ValueError(
                "APS_HYDROGEN_STATION_TIMEOUT_SECONDS must be greater than zero"
            )
        if self.hydrogen_station_cache_ttl_seconds < 0:
            raise ValueError(
                "APS_HYDROGEN_STATION_CACHE_TTL_SECONDS must not be negative"
            )

    @classmethod
    def from_env(cls) -> "Settings":
        configured_origins = os.getenv("APS_CORS_ORIGINS")
        cors_origins = (
            tuple(origin.strip() for origin in configured_origins.split(",") if origin.strip())
            if configured_origins
            else DEFAULT_CORS_ORIGINS
        )
        database_path = Path(
            os.getenv("APS_DATABASE_PATH", PROJECT_DIR / "data" / "auto_progress.db")
        )
        manual_source_dir = Path(
            os.getenv("APS_MANUAL_SOURCE_DIR", PROJECT_DIR / "data" / "manuals")
        )
        manual_search_mode = os.getenv(
            "APS_MANUAL_SEARCH_MODE", "keyword"
        ).strip().lower()
        manual_answer_mode = os.getenv(
            "APS_MANUAL_ANSWER_MODE", "extractive"
        ).strip().lower()
        configured_model_path = os.getenv("APS_MANUAL_GENERATION_MODEL_PATH")
        configured_station_catalog_path = os.getenv("APS_STATION_CATALOG_PATH")
        configured_ev_regions = os.getenv("APS_EV_CHARGER_REGION_CODES", "")
        return cls(
            database_path=database_path,
            cors_origins=cors_origins,
            manual_source_dir=manual_source_dir,
            manual_search_mode=manual_search_mode,  # type: ignore[arg-type]
            manual_embedding_model=os.getenv(
                "APS_MANUAL_EMBEDDING_MODEL", "intfloat/multilingual-e5-small"
            ),
            manual_embedding_revision=os.getenv(
                "APS_MANUAL_EMBEDDING_REVISION",
                "614241f622f53c4eeff9890bdc4f31cfecc418b3",
            ),
            manual_embedding_file=os.getenv(
                "APS_MANUAL_EMBEDDING_FILE", "openvino/openvino_model.xml"
            ),
            manual_embedding_min_score=float(
                os.getenv("APS_MANUAL_EMBEDDING_MIN_SCORE", "0.82")
            ),
            manual_answer_mode=manual_answer_mode,  # type: ignore[arg-type]
            manual_generation_model_path=(
                Path(configured_model_path) if configured_model_path else None
            ),
            manual_generation_device=os.getenv(
                "APS_MANUAL_GENERATION_DEVICE", "CPU"
            ),
            manual_generation_max_new_tokens=int(
                os.getenv("APS_MANUAL_GENERATION_MAX_NEW_TOKENS", "160")
            ),
            manual_grounding_min_token_overlap=float(
                os.getenv("APS_MANUAL_GROUNDING_MIN_TOKEN_OVERLAP", "0.55")
            ),
            naver_maps_client_id=(
                os.getenv("APS_NAVER_MAPS_CLIENT_ID", "").strip() or None
            ),
            naver_maps_client_secret=(
                os.getenv("APS_NAVER_MAPS_CLIENT_SECRET", "").strip() or None
            ),
            naver_maps_browser_client_id=(
                os.getenv("APS_NAVER_MAPS_BROWSER_CLIENT_ID", "").strip() or None
            ),
            naver_maps_timeout_seconds=float(
                os.getenv("APS_NAVER_MAPS_TIMEOUT_SECONDS", "5")
            ),
            station_catalog_path=(
                Path(configured_station_catalog_path)
                if configured_station_catalog_path
                else None
            ),
            ev_charger_service_key=(
                os.getenv("APS_EV_CHARGER_SERVICE_KEY", "").strip() or None
            ),
            ev_charger_timeout_seconds=float(
                os.getenv("APS_EV_CHARGER_TIMEOUT_SECONDS", "10")
            ),
            ev_charger_cache_ttl_seconds=float(
                os.getenv("APS_EV_CHARGER_CACHE_TTL_SECONDS", "1800")
            ),
            ev_charger_page_size=int(
                os.getenv("APS_EV_CHARGER_PAGE_SIZE", "9999")
            ),
            ev_charger_max_pages=int(
                os.getenv("APS_EV_CHARGER_MAX_PAGES", "100")
            ),
            ev_charger_region_codes=tuple(
                dict.fromkeys(
                    code.strip()
                    for code in configured_ev_regions.split(",")
                    if code.strip()
                )
            ),
            hydrogen_station_service_key=(
                os.getenv("APS_HYDROGEN_STATION_SERVICE_KEY", "").strip() or None
            ),
            hydrogen_station_timeout_seconds=float(
                os.getenv("APS_HYDROGEN_STATION_TIMEOUT_SECONDS", "10")
            ),
            hydrogen_station_cache_ttl_seconds=float(
                os.getenv("APS_HYDROGEN_STATION_CACHE_TTL_SECONDS", "300")
            ),
        )
