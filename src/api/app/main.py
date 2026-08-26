from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .database import initialize_database
from .errors import install_error_handlers
from .routes import router


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        initialize_database(resolved_settings.database_path)
        app.state.settings = resolved_settings
        yield

    application = FastAPI(
        title="자동진행단 자동차 AI 코파일럿 API",
        version="0.1.0",
        description=(
            "차량 프로필, 매뉴얼 검색과 리콜 조회를 위한 백엔드 계약입니다. "
            "현재 RAG와 외부 리콜 데이터는 아직 연결되지 않았습니다."
        ),
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    install_error_handlers(application)
    application.include_router(router)
    return application


app = create_app()
