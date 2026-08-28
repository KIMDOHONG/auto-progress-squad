from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


ManufacturerAdapterId = Literal["bmw", "chevrolet", "kgm"]
IdentificationMode = Literal["vin", "model-year-generation"]
IntegrationMode = Literal["server-only", "official-link"]
LookupStatus = Literal["permission-required", "manifest-required"]
ImagePolicy = Literal["none", "ephemeral-only"]


@dataclass(frozen=True)
class ManualAdapterCapability:
    id: ManufacturerAdapterId
    manufacturer: str
    official_url: str
    identification_mode: IdentificationMode
    integration_mode: IntegrationMode
    lookup_status: LookupStatus
    stores_raw_identifier: bool
    image_policy: ImagePolicy
    failure_code: str


@dataclass(frozen=True)
class ManualLookupRequest:
    manufacturer_id: ManufacturerAdapterId
    locale: str = "ko-KR"
    vin: str | None = field(default=None, repr=False, compare=False)
    model: str | None = None
    model_year: int | None = None

    @property
    def masked_identifier(self) -> str | None:
        if self.vin is None:
            return None
        return mask_vin(self.vin)


@dataclass(frozen=True)
class ManualLookupResult:
    manufacturer_id: ManufacturerAdapterId
    model_name: str
    model_year: int
    manual_title: str
    official_url: str
    image_url: str | None = None
    image_policy: ImagePolicy = "none"


class ManualAdapterError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ManufacturerManualAdapter(Protocol):
    @property
    def capability(self) -> ManualAdapterCapability: ...

    def resolve(self, request: ManualLookupRequest) -> ManualLookupResult: ...


def normalize_vin(value: str) -> str:
    vin = value.strip().upper()
    if len(vin) != 17 or not vin.isalnum() or any(char in vin for char in "IOQ"):
        raise ManualAdapterError(
            "invalid_vin",
            "VIN은 I, O, Q를 제외한 영문 대문자와 숫자 17자리여야 합니다.",
        )
    return vin


def mask_vin(value: str) -> str:
    vin = normalize_vin(value)
    return f"{vin[:3]}{'*' * 10}{vin[-4:]}"


class BmwDriverGuideAdapter:
    """Fail-closed BMW boundary until external-use permission is confirmed.

    The official browser application encrypts a VIN before requesting the manual,
    but its API does not allow this web application's origin. A future live
    implementation therefore belongs on the server and must keep the raw VIN out
    of URLs, logs, database rows, and persisted job payloads.
    """

    capability = ManualAdapterCapability(
        id="bmw",
        manufacturer="BMW",
        official_url=(
            "https://www.bmw.co.kr/ko/topics/owners/online-manual/"
            "bmw-driver-guide.html"
        ),
        identification_mode="vin",
        integration_mode="server-only",
        lookup_status="permission-required",
        stores_raw_identifier=False,
        image_policy="none",
        failure_code="bmw_driver_guide_permission_required",
    )

    def resolve(self, request: ManualLookupRequest) -> ManualLookupResult:
        if request.vin is None:
            raise ManualAdapterError(
                "vin_required",
                "BMW Driver's Guide 조회에는 17자리 VIN이 필요합니다.",
            )
        normalize_vin(request.vin)
        raise ManualAdapterError(
            self.capability.failure_code,
            "BMW Driver's Guide 외부 연동 사용 허가가 확인되지 않아 조회하지 않았습니다.",
        )


class PlannedOfficialLinkAdapter:
    def __init__(self, capability: ManualAdapterCapability) -> None:
        self.capability = capability

    def resolve(self, _request: ManualLookupRequest) -> ManualLookupResult:
        raise ManualAdapterError(
            self.capability.failure_code,
            f"{self.capability.manufacturer} 모델별 취급설명서 식별은 아직 연결되지 않았습니다.",
        )


_ADAPTERS: dict[ManufacturerAdapterId, ManufacturerManualAdapter] = {
    "bmw": BmwDriverGuideAdapter(),
    "chevrolet": PlannedOfficialLinkAdapter(
        ManualAdapterCapability(
            id="chevrolet",
            manufacturer="쉐보레",
            official_url="https://www.chevrolet.co.kr/owner-manuals",
            identification_mode="model-year-generation",
            integration_mode="official-link",
            lookup_status="manifest-required",
            stores_raw_identifier=False,
            image_policy="none",
            failure_code="chevrolet_manual_mapping_required",
        )
    ),
    "kgm": PlannedOfficialLinkAdapter(
        ManualAdapterCapability(
            id="kgm",
            manufacturer="KGM",
            official_url=(
                "https://www.kg-mobility.com/sr/update-download/"
                "download-center/instruction-manual"
            ),
            identification_mode="model-year-generation",
            integration_mode="official-link",
            lookup_status="manifest-required",
            stores_raw_identifier=False,
            image_policy="none",
            failure_code="kgm_manual_mapping_required",
        )
    ),
}


def list_manual_adapter_capabilities() -> list[ManualAdapterCapability]:
    return [adapter.capability for adapter in _ADAPTERS.values()]


def get_manual_adapter(
    adapter_id: ManufacturerAdapterId,
) -> ManufacturerManualAdapter:
    return _ADAPTERS[adapter_id]
