from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "https://kimdohong.github.io",
)


@dataclass(frozen=True, slots=True)
class Settings:
    database_path: Path
    cors_origins: tuple[str, ...]

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
        return cls(database_path=database_path, cors_origins=cors_origins)
