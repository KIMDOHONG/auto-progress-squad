from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .database import initialize_database
from .errors import install_error_handlers
from .manual_embedding_search import EmbeddingManualSearcher
from .manual_grounded_answer import OpenVINOGroundedAnswerGenerator
from .routes import router


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        initialize_database(resolved_settings.database_path)
        app.state.settings = resolved_settings
        app.state.manual_embedding_search = (
            EmbeddingManualSearcher(
                model_name=resolved_settings.manual_embedding_model,
                revision=resolved_settings.manual_embedding_revision,
                model_file=resolved_settings.manual_embedding_file,
                min_score=resolved_settings.manual_embedding_min_score,
            )
            if resolved_settings.manual_search_mode == "embedding"
            else None
        )
        app.state.manual_answer_generator = (
            OpenVINOGroundedAnswerGenerator(
                model_path=resolved_settings.manual_generation_model_path,
                device=resolved_settings.manual_generation_device,
                max_new_tokens=resolved_settings.manual_generation_max_new_tokens,
                min_token_overlap=(
                    resolved_settings.manual_grounding_min_token_overlap
                ),
            )
            if resolved_settings.manual_answer_mode == "openvino"
            else None
        )
        yield

    application = FastAPI(
        title="자동진행단 자동차 AI 코파일럿 API",
        version="0.1.0",
        description=(
            "차량 프로필, 승인된 매뉴얼의 출처 검색과 리콜 조회를 위한 백엔드입니다. "
            "생성형 매뉴얼 답변은 명시적인 OpenVINO 설정에서만 사용하며, "
            "외부 리콜 데이터는 아직 연결되지 않았습니다."
        ),
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    install_error_handlers(application)
    application.include_router(router)
    return application


app = create_app()
