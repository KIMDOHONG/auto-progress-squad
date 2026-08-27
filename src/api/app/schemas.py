from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


Powertrain = Literal["electric", "hydrogen", "gasoline", "diesel", "hybrid"]
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


class VehiclePayload(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)
    manufacturer: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    model_year: int = Field(ge=1990, le=2100)
    powertrain: Powertrain
    fuel_grade: FuelGrade | None = None
    battery_capacity_kwh: float | None = Field(default=None, gt=0, le=500)

    @model_validator(mode="after")
    def validate_energy_fields(self) -> "VehiclePayload":
        if self.powertrain == "electric" and self.fuel_grade is not None:
            raise ValueError("전기차에는 지정 연료를 설정할 수 없습니다.")
        if self.powertrain == "hydrogen" and self.fuel_grade is not None:
            raise ValueError("수소전기차에는 휘발유·경유 등급을 설정할 수 없습니다.")
        if self.powertrain != "electric" and self.battery_capacity_kwh is not None:
            raise ValueError("수소전기차·내연기관·하이브리드 차량에는 배터리 용량을 설정할 수 없습니다.")
        return self


class VehicleCreate(VehiclePayload):
    id: str = Field(min_length=1, max_length=100)


class VehicleUpdate(VehiclePayload):
    pass


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
