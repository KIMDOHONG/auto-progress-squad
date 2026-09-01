from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


Powertrain = Literal["electric", "hydrogen", "gasoline", "diesel", "hybrid"]
FuelGrade = Literal["regular", "premium", "super-premium", "diesel", "high-cetane"]
ManualSiteId = Literal["hmc", "kia", "genesis", "chevrolet", "kgm"]
ManualIngestionState = Literal["unavailable", "pending", "ready", "failed"]
ManufacturerAdapterId = Literal["bmw", "chevrolet", "kgm"]


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
    manual_site_id: ManualSiteId | None = None
    manual_model_name: str | None = None
    manual_project_code: str | None = None
    manual_generation: str | None = None
    manual_model_year: int | None = None
    manual_image_url: str | None = None
    manual_title: str | None = None
    manual_source_url: str | None = None
    manual_verified_at: str | None = None
    is_active: bool


class VehiclePayload(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)
    manufacturer: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    model_year: int = Field(ge=1990, le=2100)
    powertrain: Powertrain
    fuel_grade: FuelGrade | None = None
    battery_capacity_kwh: float | None = Field(default=None, gt=0, le=500)
    manual_site_id: ManualSiteId | None = None
    manual_model_name: str | None = Field(default=None, max_length=120)
    manual_project_code: str | None = Field(default=None, max_length=40)
    manual_generation: str | None = Field(default=None, max_length=80)
    manual_model_year: int | None = Field(default=None, ge=1990, le=2100)
    manual_image_url: str | None = Field(default=None, max_length=1000)
    manual_title: str | None = Field(default=None, max_length=200)
    manual_source_url: str | None = Field(default=None, max_length=1000)
    manual_verified_at: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def validate_energy_fields(self) -> "VehiclePayload":
        if self.powertrain == "electric" and self.fuel_grade is not None:
            raise ValueError("전기차에는 지정 연료를 설정할 수 없습니다.")
        if self.powertrain == "hydrogen" and self.fuel_grade is not None:
            raise ValueError("수소전기차에는 휘발유·경유 등급을 설정할 수 없습니다.")
        if self.powertrain != "electric" and self.battery_capacity_kwh is not None:
            raise ValueError("수소전기차·내연기관·하이브리드 차량에는 배터리 용량을 설정할 수 없습니다.")
        manual_values = (
            self.manual_model_name,
            self.manual_project_code,
            self.manual_generation,
            self.manual_model_year,
            self.manual_image_url,
            self.manual_title,
            self.manual_source_url,
            self.manual_verified_at,
        )
        if self.manual_site_id is None:
            if any(value is not None for value in manual_values):
                raise ValueError("공식 취급설명서 검증 정보는 일부만 저장할 수 없습니다.")
            return self

        if self.manual_model_year != self.model_year:
            raise ValueError("차량 연식과 공식 취급설명서 연식이 일치해야 합니다.")

        if self.manual_site_id in {"hmc", "kia", "genesis"}:
            required = (
                self.manual_model_name,
                self.manual_project_code,
                self.manual_model_year,
                self.manual_image_url,
                self.manual_verified_at,
            )
            if not all(value is not None for value in required):
                raise ValueError("공식 취급설명서 검증 정보는 일부만 저장할 수 없습니다.")
            allowed_image_prefixes = {
                "hmc": "https://ownersmanual.hyundai.com/",
                "kia": "https://ownersmanual.kia.com/",
                "genesis": "https://ownersmanual.genesis.com/",
            }
            assert self.manual_image_url is not None
            if not self.manual_image_url.startswith(
                allowed_image_prefixes[self.manual_site_id]
            ):
                raise ValueError("공식 제조사 도메인의 차량 이미지만 저장할 수 있습니다.")
            return self

        required = (
            self.manual_model_name,
            self.manual_generation,
            self.manual_model_year,
            self.manual_title,
            self.manual_source_url,
            self.manual_verified_at,
        )
        if not all(value is not None for value in required):
            raise ValueError("승인 카탈로그 연결 정보는 일부만 저장할 수 없습니다.")
        if self.manual_project_code is not None or self.manual_image_url is not None:
            raise ValueError("쉐보레·KGM 승인 매핑에는 프로젝트 코드나 이미지를 저장하지 않습니다.")
        allowed_source_prefixes = {
            "chevrolet": "https://www.chevrolet.co.kr/",
            "kgm": "https://www.kg-mobility.com/",
        }
        assert self.manual_source_url is not None
        if not self.manual_source_url.startswith(
            allowed_source_prefixes[self.manual_site_id]
        ):
            raise ValueError("공식 제조사 도메인의 매뉴얼 원문만 저장할 수 있습니다.")
        return self


class VehicleCreate(VehiclePayload):
    id: str = Field(min_length=1, max_length=100)


class VehicleUpdate(VehiclePayload):
    pass


class VehicleListResponse(BaseModel):
    items: list[VehicleProfile]
    active_vehicle_id: str | None


class ManualIngestionStatus(BaseModel):
    vehicle_id: str
    status: ManualIngestionState
    document_key: str | None = None
    source_url: str | None = None
    attempt_count: int = 0
    failure_code: str | None = None
    failure_message: str | None = None
    queued_at: str | None = None
    updated_at: str | None = None
    ready_at: str | None = None
    can_search: bool = False


class ManualSearchRequest(BaseModel):
    vehicle_id: str = Field(min_length=1)
    question: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)


class ManualSource(BaseModel):
    document_name: str
    source_url: str
    page: int | None = None
    section: str | None = None
    excerpt: str


class ManualSearchResponse(BaseModel):
    answer: str
    sources: list[ManualSource]
    search_engine: Literal["keyword-frequency-v1", "openvino-embedding-v1"]
    answer_engine: Literal["source-list-v1", "openvino-genai-grounded-v1"]
    citations: list[int]
    generated_at: str


class ManualAdapterCapabilityResponse(BaseModel):
    id: ManufacturerAdapterId
    manufacturer: str
    official_url: str
    identification_mode: Literal["vin", "model-year-generation"]
    integration_mode: Literal["server-only", "official-link"]
    lookup_status: Literal["permission-required", "manifest-required"]
    stores_raw_identifier: bool
    image_policy: Literal["none", "ephemeral-only"]
    failure_code: str


class ManualAdapterListResponse(BaseModel):
    items: list[ManualAdapterCapabilityResponse]


class ManualCatalogLookupRequest(BaseModel):
    model: str = Field(min_length=1, max_length=80)
    model_year: int = Field(ge=1990, le=2100)
    generation: str | None = Field(default=None, min_length=1, max_length=80)


class ManualCatalogAttachRequest(BaseModel):
    generation: str | None = Field(default=None, min_length=1, max_length=80)


class ManualChapterLinkResponse(BaseModel):
    title: str
    url: str


class ManualCatalogLookupResponse(BaseModel):
    manufacturer_id: Literal["chevrolet", "kgm"]
    model: str
    model_year: int
    generation: str
    manual_title: str
    official_url: str
    source_checked_at: str
    chapters: list[ManualChapterLinkResponse]


class RecallItem(BaseModel):
    recall_id: str
    title: str
    published_at: str | None = None
    source_url: str


class RecallQueryScope(BaseModel):
    manufacturer: str
    model: str
    model_year: int
    generation: str | None = None
    project_code: str | None = None
    lookup_key: str


class RecallListResponse(BaseModel):
    vehicle_id: str
    status: Literal["matched", "no_results"]
    query: RecallQueryScope
    items: list[RecallItem]
    source_name: str
    source_url: str
    retrieved_at: str
