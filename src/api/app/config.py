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
ManualSearchMode = Literal["keyword", "embedding"]


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

    def __post_init__(self) -> None:
        if self.manual_search_mode not in {"keyword", "embedding"}:
            raise ValueError("APS_MANUAL_SEARCH_MODE must be keyword or embedding")
        if not 0 <= self.manual_embedding_min_score <= 1:
            raise ValueError("APS_MANUAL_EMBEDDING_MIN_SCORE must be between 0 and 1")

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
        )
