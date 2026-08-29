from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response, status

from .database import (
    LastVehicleDeletionError,
    VehicleLimitReachedError,
    VehicleNotFoundError,
    activate_vehicle,
    create_vehicle,
    database_is_ready,
    delete_vehicle,
    get_vehicle_row,
    get_manual_ingestion_row,
    list_manual_chunk_rows,
    list_vehicle_rows,
    manual_document_is_indexed,
    retry_manual_ingestion,
    update_vehicle,
)
from .errors import ApiError, ServiceNotConfiguredError
from .manual_adapter_catalog import (
    CATALOG_MANUFACTURERS,
    ManualAdapterCatalogError,
    load_manual_adapter_catalog,
    resolve_manual_catalog_entry,
)
from .manual_adapters import list_manual_adapter_capabilities
from .manual_embedding_search import ManualEmbeddingSearchError
from .manual_grounded_answer import (
    ManualAnswerGenerationError,
    ManualAnswerValidationError,
)
from .manual_ingestion import search_manual_document
from .schemas import (
    ApiErrorResponse,
    HealthResponse,
    ManualSearchRequest,
    ManualSearchResponse,
    ManualAdapterCapabilityResponse,
    ManualAdapterListResponse,
    ManualCatalogAttachRequest,
    ManualCatalogLookupRequest,
    ManualCatalogLookupResponse,
    ManualIngestionStatus,
    RecallListResponse,
    VehicleCreate,
    VehicleListResponse,
    VehicleProfile,
    VehicleUpdate,
)


router = APIRouter(prefix="/api/v1")


def vehicle_from_row(row: sqlite3.Row) -> VehicleProfile:
    record = dict(row)
    record["is_active"] = bool(record["is_active"])
    return VehicleProfile(**record)


def vehicle_not_found() -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, "vehicle_not_found", "차량을 찾을 수 없습니다.")


def manual_ingestion_from_row(
    vehicle_id: str, row: sqlite3.Row | None
) -> ManualIngestionStatus:
    if row is None:
        return ManualIngestionStatus(vehicle_id=vehicle_id, status="unavailable")
    record = dict(row)
    record["can_search"] = record["status"] == "ready"
    return ManualIngestionStatus(**record)


def manual_catalog_api_error(error: ManualAdapterCatalogError) -> ApiError:
    if error.code in {
        "manual_adapter_catalog_not_found",
        "manual_adapter_catalog_invalid",
        "manual_adapter_catalog_duplicate_chapter",
        "manual_adapter_catalog_duplicate_mapping",
        "manual_adapter_source_not_allowed",
    }:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif error.code == "manual_generation_required":
        status_code = status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_404_NOT_FOUND
    return ApiError(
        status_code,
        error.code,
        error.message,
        details=error.details,
    )


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    if not database_is_ready(settings.database_path):
        raise ServiceNotConfiguredError(
            code="database_not_ready",
            message="차량 데이터베이스가 준비되지 않았습니다.",
        )
    return HealthResponse(
        status="ok",
        service="auto-progress-squad-api",
        version="0.1.0",
        database="ready",
    )


@router.get(
    "/manual-adapters",
    response_model=ManualAdapterListResponse,
    tags=["manual"],
)
def list_manual_adapters() -> ManualAdapterListResponse:
    return ManualAdapterListResponse(
        items=[
            ManualAdapterCapabilityResponse(**asdict(capability))
            for capability in list_manual_adapter_capabilities()
        ]
    )


@router.post(
    "/manual-adapters/{adapter_id}/resolve",
    response_model=ManualCatalogLookupResponse,
    responses={
        404: {"model": ApiErrorResponse},
        409: {"model": ApiErrorResponse},
        503: {"model": ApiErrorResponse},
    },
    tags=["manual"],
)
def resolve_manual_adapter(
    request: Request,
    adapter_id: str,
    payload: ManualCatalogLookupRequest,
) -> ManualCatalogLookupResponse:
    if adapter_id not in CATALOG_MANUFACTURERS:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "manual_adapter_catalog_not_supported",
            "이 제조사는 승인 카탈로그 방식으로 조회하지 않습니다.",
        )
    try:
        entries = load_manual_adapter_catalog(
            request.app.state.settings.manual_source_dir
        )
        entry = resolve_manual_catalog_entry(
            entries,
            manufacturer_id=adapter_id,
            model=payload.model,
            model_year=payload.model_year,
            generation=payload.generation,
        )
    except ManualAdapterCatalogError as error:
        raise manual_catalog_api_error(error) from None

    return ManualCatalogLookupResponse(
        manufacturer_id=entry.manufacturer_id,
        model=entry.model,
        model_year=entry.model_year,
        generation=entry.generation,
        manual_title=entry.manual_title,
        official_url=entry.official_url,
        source_checked_at=entry.source_checked_at,
        chapters=[asdict(chapter) for chapter in entry.chapters],
    )


@router.post(
    "/vehicles/{vehicle_id}/manual-adapters/{adapter_id}",
    response_model=VehicleProfile,
    responses={
        404: {"model": ApiErrorResponse},
        409: {"model": ApiErrorResponse},
        503: {"model": ApiErrorResponse},
    },
    tags=["manual", "vehicles"],
)
def attach_manual_adapter(
    request: Request,
    vehicle_id: str,
    adapter_id: str,
    payload: ManualCatalogAttachRequest,
) -> VehicleProfile:
    if adapter_id not in CATALOG_MANUFACTURERS:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "manual_adapter_catalog_not_supported",
            "이 제조사는 승인 카탈로그 방식으로 연결하지 않습니다.",
        )
    try:
        vehicle_row = get_vehicle_row(
            request.app.state.settings.database_path, vehicle_id
        )
    except VehicleNotFoundError:
        raise vehicle_not_found() from None

    manufacturer_aliases = {
        "chevrolet": {"쉐보레", "chevrolet"},
        "kgm": {"kgm", "kg모빌리티", "kg mobility", "쌍용", "쌍용자동차"},
    }
    if str(vehicle_row["manufacturer"]).strip().casefold() not in {
        alias.casefold() for alias in manufacturer_aliases[adapter_id]
    }:
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "manual_adapter_manufacturer_mismatch",
            "차량 제조사와 선택한 매뉴얼 어댑터가 일치하지 않습니다.",
        )

    try:
        entries = load_manual_adapter_catalog(
            request.app.state.settings.manual_source_dir
        )
        entry = resolve_manual_catalog_entry(
            entries,
            manufacturer_id=adapter_id,
            model=str(vehicle_row["model"]),
            model_year=int(vehicle_row["model_year"]),
            generation=payload.generation,
        )
    except ManualAdapterCatalogError as error:
        raise manual_catalog_api_error(error) from None

    values = dict(vehicle_row)
    values.update(
        {
            "manual_site_id": entry.manufacturer_id,
            "manual_model_name": entry.model,
            "manual_project_code": None,
            "manual_generation": entry.generation,
            "manual_model_year": entry.model_year,
            "manual_image_url": None,
            "manual_title": entry.manual_title,
            "manual_source_url": entry.official_url,
            "manual_verified_at": entry.source_checked_at,
        }
    )
    values.pop("id", None)
    values.pop("is_active", None)
    validated = VehicleUpdate(**values)
    row = update_vehicle(
        request.app.state.settings.database_path,
        vehicle_id,
        validated.model_dump(),
    )
    return vehicle_from_row(row)


@router.get("/vehicles", response_model=VehicleListResponse, tags=["vehicles"])
def list_vehicles(request: Request) -> VehicleListResponse:
    rows = list_vehicle_rows(request.app.state.settings.database_path)
    items = [vehicle_from_row(row) for row in rows]
    active_vehicle_id = next((item.id for item in items if item.is_active), None)
    return VehicleListResponse(items=items, active_vehicle_id=active_vehicle_id)


@router.post(
    "/vehicles",
    response_model=VehicleProfile,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ApiErrorResponse}},
    tags=["vehicles"],
)
def add_vehicle(request: Request, payload: VehicleCreate) -> VehicleProfile:
    try:
        row = create_vehicle(
            request.app.state.settings.database_path, payload.model_dump()
        )
    except VehicleLimitReachedError:
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "vehicle_limit_reached",
            "차량은 최대 3대까지 등록할 수 있습니다.",
        ) from None
    except sqlite3.IntegrityError:
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "vehicle_already_exists",
            "같은 식별자의 차량이 이미 등록되어 있습니다.",
        ) from None
    return vehicle_from_row(row)


@router.put(
    "/vehicles/{vehicle_id}",
    response_model=VehicleProfile,
    responses={404: {"model": ApiErrorResponse}},
    tags=["vehicles"],
)
def edit_vehicle(
    request: Request, vehicle_id: str, payload: VehicleUpdate
) -> VehicleProfile:
    try:
        row = update_vehicle(
            request.app.state.settings.database_path,
            vehicle_id,
            payload.model_dump(),
        )
    except VehicleNotFoundError:
        raise vehicle_not_found() from None
    return vehicle_from_row(row)


@router.put(
    "/vehicles/{vehicle_id}/active",
    response_model=VehicleProfile,
    responses={404: {"model": ApiErrorResponse}},
    tags=["vehicles"],
)
def set_active_vehicle(request: Request, vehicle_id: str) -> VehicleProfile:
    try:
        row = activate_vehicle(request.app.state.settings.database_path, vehicle_id)
    except VehicleNotFoundError:
        raise vehicle_not_found() from None
    return vehicle_from_row(row)


@router.delete(
    "/vehicles/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ApiErrorResponse}, 409: {"model": ApiErrorResponse}},
    tags=["vehicles"],
)
def remove_vehicle(request: Request, vehicle_id: str) -> Response:
    try:
        delete_vehicle(request.app.state.settings.database_path, vehicle_id)
    except VehicleNotFoundError:
        raise vehicle_not_found() from None
    except LastVehicleDeletionError:
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "last_vehicle_required",
            "마지막 차량은 삭제할 수 없습니다.",
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/vehicles/{vehicle_id}/manual-ingestion",
    response_model=ManualIngestionStatus,
    responses={404: {"model": ApiErrorResponse}},
    tags=["manual"],
)
def get_manual_ingestion(
    request: Request, vehicle_id: str
) -> ManualIngestionStatus:
    try:
        row = get_manual_ingestion_row(
            request.app.state.settings.database_path, vehicle_id
        )
    except VehicleNotFoundError:
        raise vehicle_not_found() from None
    return manual_ingestion_from_row(vehicle_id, row)


@router.post(
    "/vehicles/{vehicle_id}/manual-ingestion/retry",
    response_model=ManualIngestionStatus,
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": ApiErrorResponse}, 409: {"model": ApiErrorResponse}},
    tags=["manual"],
)
def retry_vehicle_manual_ingestion(
    request: Request, vehicle_id: str
) -> ManualIngestionStatus:
    try:
        row = retry_manual_ingestion(
            request.app.state.settings.database_path, vehicle_id
        )
    except VehicleNotFoundError:
        raise vehicle_not_found() from None
    except ValueError:
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "verified_manual_required",
            "정확한 공식 취급설명서가 확인된 차량만 문서 준비를 시작할 수 있습니다.",
        ) from None
    return manual_ingestion_from_row(vehicle_id, row)


@router.post(
    "/manual/search",
    response_model=ManualSearchResponse,
    responses={
        404: {"model": ApiErrorResponse},
        409: {"model": ApiErrorResponse},
        503: {"model": ApiErrorResponse},
    },
    tags=["manual"],
)
def search_manual(request: Request, payload: ManualSearchRequest) -> ManualSearchResponse:
    try:
        ingestion = get_manual_ingestion_row(
            request.app.state.settings.database_path, payload.vehicle_id
        )
    except VehicleNotFoundError:
        raise vehicle_not_found() from None
    if ingestion is None:
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "verified_manual_required",
            "정확한 공식 취급설명서가 확인되기 전에는 매뉴얼 검색을 사용할 수 없습니다.",
        )
    if ingestion["status"] == "pending":
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "manual_ingestion_pending",
            "취급설명서를 확인 중입니다. 준비가 끝난 뒤 다시 시도해 주세요.",
            retryable=True,
        )
    if ingestion["status"] == "failed":
        raise ApiError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "manual_ingestion_failed",
            "취급설명서 준비에 실패했습니다. 재시도 후 상태를 확인해 주세요.",
            retryable=True,
        )
    document_key = str(ingestion["document_key"])
    if not manual_document_is_indexed(
        request.app.state.settings.database_path, document_key
    ):
        raise ServiceNotConfiguredError(
            code="manual_index_not_ready",
            message="취급설명서 상태와 검색 인덱스가 일치하지 않습니다. 문서를 다시 준비해 주세요.",
        )
    search_engine = "keyword-frequency-v1"
    if request.app.state.settings.manual_search_mode == "embedding":
        search_engine = "openvino-embedding-v1"
        try:
            sources = request.app.state.manual_embedding_search.search(
                list_manual_chunk_rows(
                    request.app.state.settings.database_path, document_key
                ),
                document_key=document_key,
                question=payload.question,
                limit=payload.limit,
            )
        except ManualEmbeddingSearchError:
            raise ApiError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "manual_embedding_unavailable",
                "매뉴얼 의미 검색 모델을 사용할 수 없습니다. 서버 설정과 모델 상태를 확인해 주세요.",
                retryable=True,
            ) from None
    else:
        sources = search_manual_document(
            request.app.state.settings.database_path,
            document_key,
            payload.question,
            payload.limit,
        )
    answer_engine = "source-list-v1"
    citations: list[int] = []
    if not sources:
        answer = "현재 질문과 일치하는 내용을 이 차량의 공식 취급설명서에서 찾지 못했습니다."
    elif request.app.state.settings.manual_answer_mode == "openvino":
        try:
            grounded_answer = request.app.state.manual_answer_generator.generate(
                payload.question, sources
            )
        except ManualAnswerGenerationError:
            raise ApiError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "manual_answer_generation_unavailable",
                "로컬 생성 답변 모델을 사용할 수 없습니다. 서버 설정과 모델 상태를 확인해 주세요.",
                retryable=True,
            ) from None
        except ManualAnswerValidationError:
            raise ApiError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "manual_answer_validation_failed",
                "생성 답변이 검색 근거와 인용 검증을 통과하지 못했습니다. 원문 출처를 직접 확인해 주세요.",
                retryable=True,
            ) from None
        answer = grounded_answer.answer
        citations = list(grounded_answer.citations)
        answer_engine = "openvino-genai-grounded-v1"
    else:
        answer = "공식 취급설명서에서 관련 내용을 찾았습니다. 아래 출처의 원문을 확인해 주세요."
    return ManualSearchResponse(
        answer=answer,
        sources=sources,
        search_engine=search_engine,
        answer_engine=answer_engine,
        citations=citations,
        generated_at=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/vehicles/{vehicle_id}/recalls",
    response_model=RecallListResponse,
    responses={503: {"model": ApiErrorResponse}},
    tags=["recalls"],
)
def list_recalls(vehicle_id: str) -> RecallListResponse:
    if not vehicle_id.strip():
        raise ServiceNotConfiguredError(
            code="vehicle_id_required", message="차량 식별자가 필요합니다."
        )
    raise ServiceNotConfiguredError(
        code="recall_source_not_configured",
        message="공식 리콜 데이터 원천이 아직 연결되지 않았습니다.",
    )
