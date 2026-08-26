from __future__ import annotations

from fastapi import APIRouter, Request

from .database import database_is_ready, list_vehicle_rows
from .errors import ServiceNotConfiguredError
from .schemas import (
    ApiErrorResponse,
    HealthResponse,
    ManualSearchRequest,
    ManualSearchResponse,
    RecallListResponse,
    VehicleListResponse,
    VehicleProfile,
)


router = APIRouter(prefix="/api/v1")


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


@router.get("/vehicles", response_model=VehicleListResponse, tags=["vehicles"])
def list_vehicles(request: Request) -> VehicleListResponse:
    rows = list_vehicle_rows(request.app.state.settings.database_path)
    items = []
    for row in rows:
        record = dict(row)
        record["is_active"] = bool(record["is_active"])
        items.append(VehicleProfile(**record))
    active_vehicle_id = next((item.id for item in items if item.is_active), None)
    return VehicleListResponse(items=items, active_vehicle_id=active_vehicle_id)


@router.post(
    "/manual/search",
    response_model=ManualSearchResponse,
    responses={503: {"model": ApiErrorResponse}},
    tags=["manual"],
)
def search_manual(_payload: ManualSearchRequest) -> ManualSearchResponse:
    raise ServiceNotConfiguredError(
        code="manual_rag_not_configured",
        message="차량 매뉴얼 RAG 데이터가 아직 연결되지 않았습니다.",
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
