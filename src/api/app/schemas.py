from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Powertrain = Literal["electric", "gasoline", "diesel", "hybrid"]
FuelGrade = Literal["regular", "premium", "super-premium", "diesel", "high-cetane"]


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: list[dict[str, object]] | None = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorDetail


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    database: Literal["ready"]


class VehicleProfile(BaseModel):
    id: str
    nickname: str
    manufacturer: str
    model: str
    model_year: int
    powertrain: Powertrain
    fuel_grade: FuelGrade | None = None
    battery_capacity_kwh: float | None = None
    is_active: bool


class VehicleListResponse(BaseModel):
    items: list[VehicleProfile]
    active_vehicle_id: str | None


class ManualSearchRequest(BaseModel):
    vehicle_id: str = Field(min_length=1)
    question: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)


class ManualSource(BaseModel):
    document_name: str
    page: int | None = None
    section: str | None = None
    excerpt: str


class ManualSearchResponse(BaseModel):
    answer: str
    sources: list[ManualSource]
    generated_at: str


class RecallItem(BaseModel):
    recall_id: str
    title: str
    published_at: str | None = None
    source_url: str


class RecallListResponse(BaseModel):
    vehicle_id: str
    items: list[RecallItem]
    retrieved_at: str
