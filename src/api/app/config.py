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
ManualAnswerMode = Literal["source-list", "openvino"]


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
    manual_answer_mode: ManualAnswerMode = "source-list"
    manual_generation_model_path: Path | None = None
    manual_generation_device: str = "CPU"
    manual_generation_max_new_tokens: int = 256
    manual_grounding_min_token_overlap: float = 0.55

    def __post_init__(self) -> None:
        if self.manual_search_mode not in {"keyword", "embedding"}:
            raise ValueError("APS_MANUAL_SEARCH_MODE must be keyword or embedding")
        if not 0 <= self.manual_embedding_min_score <= 1:
            raise ValueError("APS_MANUAL_EMBEDDING_MIN_SCORE must be between 0 and 1")
        if self.manual_answer_mode not in {"source-list", "openvino"}:
            raise ValueError("APS_MANUAL_ANSWER_MODE must be source-list or openvino")
        if not self.manual_generation_device.strip():
            raise ValueError("APS_MANUAL_GENERATION_DEVICE must not be empty")
        if self.manual_generation_max_new_tokens < 1:
            raise ValueError("APS_MANUAL_GENERATION_MAX_NEW_TOKENS must be at least 1")
        if not 0 <= self.manual_grounding_min_token_overlap <= 1:
            raise ValueError(
                "APS_MANUAL_GROUNDING_MIN_TOKEN_OVERLAP must be between 0 and 1"
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
            "APS_MANUAL_ANSWER_MODE", "source-list"
        ).strip().lower()
        configured_model_path = os.getenv("APS_MANUAL_GENERATION_MODEL_PATH")
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
                os.getenv("APS_MANUAL_GENERATION_MAX_NEW_TOKENS", "256")
            ),
            manual_grounding_min_token_overlap=float(
                os.getenv("APS_MANUAL_GROUNDING_MIN_TOKEN_OVERLAP", "0.55")
            ),
        )
