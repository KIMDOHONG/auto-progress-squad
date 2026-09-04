from __future__ import annotations

import json
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode, urlparse
from urllib.request import Request, urlopen


EnergyKind = Literal["electric", "hydrogen", "fuel"]
StationStatus = Literal["available", "busy", "unavailable", "unknown"]
FuelGradeMatch = Literal["confirmed", "unknown", "not-applicable"]
StationJsonTransport = Callable[[str, float], Mapping[str, Any]]


class StationProviderError(Exception):
    """Raised when station data cannot be returned or safely interpreted."""


class StationProviderNotConfiguredError(StationProviderError):
    """Raised when the configured provider does not support an energy kind."""


@dataclass(frozen=True, slots=True)
class StationCandidate:
    station_id: str
    name: str
    address: str
    longitude: float
    latitude: float
    energy_kind: EnergyKind
    status: StationStatus = "unknown"
    status_observed_at: str | None = None
    power_kw: float | None = None
    pressure_bar: int | None = None
    queue_vehicle_count: int | None = None
    trailer_pressure_bar: float | None = None
    fuel_grades: tuple[str, ...] = ()
    source_url: str | None = None


@dataclass(frozen=True, slots=True)
class StationSourceResult:
    stations: tuple[StationCandidate, ...]
    retrieved_at: str


@dataclass(frozen=True, slots=True)
class RankedStation:
    station: StationCandidate
    distance_to_route_km: float
    route_progress_percent: float
    fuel_grade_match: FuelGradeMatch


@dataclass(frozen=True, slots=True)
class _RouteGeometry:
    reference_latitude: float
    projected_path: tuple[tuple[float, float], ...]
    segment_lengths: tuple[float, ...]
    total_length: float


class StationProvider(Protocol):
    source_name: str
    source_url: str

    def list_stations(self, energy_kind: EnergyKind) -> StationSourceResult: ...


def _default_station_json_transport(
    url: str, timeout_seconds: float
) -> Mapping[str, Any]:
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "auto-progress-squad/0.1"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        raise StationProviderError("충전·주유소 공식 API 요청에 실패했습니다.") from error
    if not isinstance(payload, Mapping):
        raise StationProviderError("충전·주유소 공식 API 응답 형식이 올바르지 않습니다.")
    return payload


def _finite_coordinate(longitude: float, latitude: float) -> bool:
    return (
        math.isfinite(longitude)
        and math.isfinite(latitude)
        and -180 <= longitude <= 180
        and -90 <= latitude <= 90
    )


def _valid_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_station_source_result(
    source_name: str, source_url: str, result: StationSourceResult
) -> None:
    if not source_name.strip() or not _valid_https_url(source_url):
        raise StationProviderError("충전·주유소 공급자 출처를 확인할 수 없습니다.")
    if not result.retrieved_at.strip():
        raise StationProviderError("충전·주유소 데이터 조회시각이 필요합니다.")
    for station in result.stations:
        if not station.station_id.strip() or not station.name.strip() or not station.address.strip():
            raise StationProviderError("충전·주유소 식별자, 이름, 주소가 필요합니다.")
        if station.source_url and not _valid_https_url(station.source_url):
            raise StationProviderError("충전·주유소 원문 URL은 HTTPS여야 합니다.")
        if station.power_kw is not None and station.power_kw <= 0:
            raise StationProviderError("충전기 출력은 0보다 커야 합니다.")
        if station.pressure_bar is not None and station.pressure_bar <= 0:
            raise StationProviderError("수소 충전 압력은 0보다 커야 합니다.")
        if station.queue_vehicle_count is not None and station.queue_vehicle_count < 0:
            raise StationProviderError("수소 충전 대기 차량 수는 음수일 수 없습니다.")
        if (
            station.trailer_pressure_bar is not None
            and station.trailer_pressure_bar < 0
        ):
            raise StationProviderError("수소 튜브트레일러 압력은 음수일 수 없습니다.")


def _project_km(
    longitude: float, latitude: float, reference_latitude: float
) -> tuple[float, float]:
    earth_radius_km = 6371.0088
    x = (
        math.radians(longitude)
        * earth_radius_km
        * math.cos(math.radians(reference_latitude))
    )
    y = math.radians(latitude) * earth_radius_km
    return x, y


def _prepare_route_geometry(
    route_path: Sequence[tuple[float, float]],
) -> _RouteGeometry:
    reference_latitude = sum(point[1] for point in route_path) / len(route_path)
    projected_path = tuple(
        _project_km(longitude, latitude, reference_latitude)
        for longitude, latitude in route_path
    )
    segment_lengths = tuple(
        math.hypot(end_x - start_x, end_y - start_y)
        for (start_x, start_y), (end_x, end_y) in zip(
            projected_path, projected_path[1:]
        )
    )
    total_length = sum(segment_lengths)
    if total_length <= 0:
        raise StationProviderError("경로 좌표가 서로 다른 두 지점을 포함해야 합니다.")
    return _RouteGeometry(
        reference_latitude=reference_latitude,
        projected_path=projected_path,
        segment_lengths=segment_lengths,
        total_length=total_length,
    )


def _route_distance(
    geometry: _RouteGeometry, station: StationCandidate
) -> tuple[float, float]:
    point_x, point_y = _project_km(
        station.longitude, station.latitude, geometry.reference_latitude
    )

    best_distance = math.inf
    best_progress = 0.0
    traversed = 0.0
    for index, ((start_x, start_y), (end_x, end_y)) in enumerate(
        zip(geometry.projected_path, geometry.projected_path[1:])
    ):
        delta_x = end_x - start_x
        delta_y = end_y - start_y
        segment_length = geometry.segment_lengths[index]
        if segment_length == 0:
            continue
        projection = (
            (point_x - start_x) * delta_x + (point_y - start_y) * delta_y
        ) / (segment_length * segment_length)
        ratio = min(1.0, max(0.0, projection))
        nearest_x = start_x + ratio * delta_x
        nearest_y = start_y + ratio * delta_y
        distance = math.hypot(point_x - nearest_x, point_y - nearest_y)
        if distance < best_distance:
            best_distance = distance
            best_progress = (
                (traversed + ratio * segment_length) / geometry.total_length * 100
            )
        traversed += segment_length
    return best_distance, best_progress


def rank_route_stations(
    route_path: Sequence[tuple[float, float]],
    stations: Sequence[StationCandidate],
    *,
    energy_kind: EnergyKind,
    corridor_km: float,
    limit: int,
    fuel_grade: str | None = None,
) -> tuple[RankedStation, ...]:
    if len(route_path) < 2 or any(
        not _finite_coordinate(longitude, latitude)
        for longitude, latitude in route_path
    ):
        raise StationProviderError("경로 좌표가 유효하지 않습니다.")
    if not math.isfinite(corridor_km) or corridor_km <= 0:
        raise StationProviderError("경로 탐색 반경은 0보다 커야 합니다.")
    if limit < 1:
        raise StationProviderError("후보 개수는 1개 이상이어야 합니다.")

    geometry = _prepare_route_geometry(route_path)
    latitude_margin = corridor_km / 110.574
    longitude_scale = max(
        0.01,
        math.cos(
            math.radians(
                max(abs(latitude) for _, latitude in route_path) + latitude_margin
            )
        ),
    )
    longitude_margin = corridor_km / (111.320 * longitude_scale)
    min_longitude = min(longitude for longitude, _ in route_path) - longitude_margin
    max_longitude = max(longitude for longitude, _ in route_path) + longitude_margin
    min_latitude = min(latitude for _, latitude in route_path) - latitude_margin
    max_latitude = max(latitude for _, latitude in route_path) + latitude_margin

    normalized_fuel_grade = fuel_grade.strip().lower() if fuel_grade else None
    ranked: list[RankedStation] = []
    for station in stations:
        if station.energy_kind != energy_kind:
            continue
        if not _finite_coordinate(station.longitude, station.latitude):
            raise StationProviderError("충전·주유소 좌표가 유효하지 않습니다.")
        if not (
            min_longitude <= station.longitude <= max_longitude
            and min_latitude <= station.latitude <= max_latitude
        ):
            continue

        fuel_grade_match: FuelGradeMatch = "not-applicable"
        if energy_kind == "fuel" and normalized_fuel_grade:
            normalized_grades = {grade.strip().lower() for grade in station.fuel_grades}
            if normalized_grades:
                if normalized_fuel_grade not in normalized_grades:
                    continue
                fuel_grade_match = "confirmed"
            else:
                fuel_grade_match = "unknown"

        distance, progress = _route_distance(geometry, station)
        if distance <= corridor_km:
            ranked.append(
                RankedStation(
                    station=station,
                    distance_to_route_km=round(distance, 2),
                    route_progress_percent=round(progress, 1),
                    fuel_grade_match=fuel_grade_match,
                )
            )

    ranked.sort(
        key=lambda candidate: (
            candidate.distance_to_route_km,
            candidate.route_progress_percent,
            candidate.station.name,
        )
    )
    return tuple(ranked[:limit])


class KecoEvChargerProvider:
    """Reads nationwide charger information from the KECO public OpenAPI."""

    source_name = "한국환경공단 전기자동차 충전소 정보"
    source_url = "https://www.data.go.kr/data/15013115/standard.do"
    _endpoint = "https://apis.data.go.kr/B552584/EvCharger/getChargerInfo"
    _seoul_timezone = timezone(timedelta(hours=9))

    def __init__(
        self,
        service_key: str,
        *,
        timeout_seconds: float = 10.0,
        cache_ttl_seconds: float = 1_800.0,
        page_size: int = 9_999,
        max_pages: int = 100,
        region_codes: Sequence[str] = (),
        transport: StationJsonTransport | None = None,
    ) -> None:
        normalized_key = unquote(service_key.strip())
        if not normalized_key:
            raise ValueError("KECO EV charger service key is required")
        if timeout_seconds <= 0:
            raise ValueError("KECO EV charger timeout must be greater than zero")
        if cache_ttl_seconds < 0:
            raise ValueError("KECO EV charger cache TTL must not be negative")
        if not 10 <= page_size <= 9_999:
            raise ValueError("KECO EV charger page size must be between 10 and 9999")
        if max_pages < 1:
            raise ValueError("KECO EV charger max pages must be at least 1")
        normalized_regions = tuple(
            dict.fromkeys(code.strip() for code in region_codes if code.strip())
        )
        if any(len(code) != 2 or not code.isdigit() for code in normalized_regions):
            raise ValueError("KECO EV charger region codes must be two digits")

        self._service_key = normalized_key
        self._timeout_seconds = timeout_seconds
        self._cache_ttl_seconds = cache_ttl_seconds
        self._page_size = page_size
        self._max_pages = max_pages
        self._region_codes = normalized_regions
        self._transport = transport or _default_station_json_transport
        self._cached_result: StationSourceResult | None = None
        self._cache_expires_at = 0.0

    @staticmethod
    def _response_body(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        response = payload.get("response")
        if isinstance(response, Mapping):
            return response
        return payload

    @classmethod
    def _page_items(
        cls, payload: Mapping[str, Any]
    ) -> tuple[list[Mapping[str, Any]], int]:
        response = cls._response_body(payload)
        header = response.get("header")
        body = response.get("body")
        header_mapping = header if isinstance(header, Mapping) else response
        body_mapping = body if isinstance(body, Mapping) else response
        result_code = str(header_mapping.get("resultCode", "")).strip()
        if result_code != "00":
            raise StationProviderError("전기차 충전소 공식 API가 요청을 처리하지 못했습니다.")

        raw_total = body_mapping.get("totalCount", response.get("totalCount", 0))
        try:
            total_count = int(raw_total)
        except (TypeError, ValueError) as error:
            raise StationProviderError("전기차 충전소 공식 API 전체 건수를 확인할 수 없습니다.") from error
        if total_count < 0:
            raise StationProviderError("전기차 충전소 공식 API 전체 건수가 올바르지 않습니다.")

        items_container = body_mapping.get("items", response.get("items"))
        if items_container in (None, ""):
            return [], total_count
        if isinstance(items_container, Mapping):
            raw_items = items_container.get("item", [])
        else:
            raw_items = items_container
        if isinstance(raw_items, Mapping):
            raw_items = [raw_items]
        if not isinstance(raw_items, list) or any(
            not isinstance(item, Mapping) for item in raw_items
        ):
            raise StationProviderError("전기차 충전소 공식 API 목록 형식이 올바르지 않습니다.")
        return [item for item in raw_items if isinstance(item, Mapping)], total_count

    def _request_page(
        self, page_number: int, region_code: str | None
    ) -> Mapping[str, Any]:
        params = {
            "serviceKey": self._service_key,
            "pageNo": str(page_number),
            "numOfRows": str(self._page_size),
            "dataType": "JSON",
        }
        if region_code:
            params["zcode"] = region_code
        return self._transport(
            f"{self._endpoint}?{urlencode(params)}", self._timeout_seconds
        )

    def _fetch_items(self) -> list[Mapping[str, Any]]:
        all_items: list[Mapping[str, Any]] = []
        regions: tuple[str | None, ...] = self._region_codes or (None,)
        for region_code in regions:
            page_number = 1
            received = 0
            while True:
                page_items, total_count = self._page_items(
                    self._request_page(page_number, region_code)
                )
                all_items.extend(page_items)
                received += len(page_items)
                if received >= total_count:
                    break
                if not page_items:
                    raise StationProviderError("전기차 충전소 공식 API 페이지가 누락되었습니다.")
                if page_number >= self._max_pages:
                    raise StationProviderError("전기차 충전소 공식 API 페이지 제한을 초과했습니다.")
                page_number += 1
        return all_items

    @classmethod
    def _parse_observed_at(cls, raw_value: Any) -> str | None:
        value = str(raw_value or "").strip()
        if not value:
            return None
        try:
            observed = datetime.strptime(value, "%Y%m%d%H%M%S").replace(
                tzinfo=cls._seoul_timezone
            )
        except ValueError:
            return None
        return observed.isoformat()

    @staticmethod
    def _parse_power_kw(raw_value: Any) -> float | None:
        try:
            power_kw = float(raw_value)
        except (TypeError, ValueError):
            return None
        return power_kw if math.isfinite(power_kw) and power_kw > 0 else None

    @staticmethod
    def _charger_status(raw_value: Any) -> StationStatus:
        value = str(raw_value or "").strip()
        if value == "2":
            return "available"
        if value in {"3", "6"}:
            return "busy"
        if value in {"1", "4", "5"}:
            return "unavailable"
        return "unknown"

    @staticmethod
    def _aggregate_status(statuses: Sequence[StationStatus]) -> StationStatus:
        if "available" in statuses:
            return "available"
        if "busy" in statuses:
            return "busy"
        if "unavailable" in statuses:
            return "unavailable"
        return "unknown"

    @classmethod
    def _normalize_stations(
        cls, items: Sequence[Mapping[str, Any]]
    ) -> tuple[StationCandidate, ...]:
        grouped: dict[str, list[Mapping[str, Any]]] = {}
        for item in items:
            station_id = str(item.get("statId", "")).strip()
            if not station_id or str(item.get("delYn", "N")).strip().upper() == "Y":
                continue
            grouped.setdefault(station_id, []).append(item)

        stations: list[StationCandidate] = []
        for station_id, chargers in grouped.items():
            first = chargers[0]
            name = str(first.get("statNm", "")).strip()
            primary_address = str(first.get("addr", "")).strip()
            detail_address = str(first.get("addrDetail", "")).strip()
            address = " ".join(part for part in (primary_address, detail_address) if part)
            try:
                latitude = float(first.get("lat"))
                longitude = float(first.get("lng"))
            except (TypeError, ValueError):
                continue
            if not name or not address or not _finite_coordinate(longitude, latitude):
                continue

            statuses = [cls._charger_status(item.get("stat")) for item in chargers]
            observed_values = [
                observed
                for observed in (
                    cls._parse_observed_at(item.get("statUpdDt")) for item in chargers
                )
                if observed is not None
            ]
            power_values = [
                power
                for power in (cls._parse_power_kw(item.get("output")) for item in chargers)
                if power is not None
            ]
            stations.append(
                StationCandidate(
                    station_id=station_id,
                    name=name,
                    address=address,
                    longitude=longitude,
                    latitude=latitude,
                    energy_kind="electric",
                    status=cls._aggregate_status(statuses),
                    status_observed_at=max(observed_values, default=None),
                    power_kw=max(power_values, default=None),
                )
            )
        return tuple(stations)

    def list_stations(self, energy_kind: EnergyKind) -> StationSourceResult:
        if energy_kind != "electric":
            raise StationProviderNotConfiguredError(
                "선택한 동력원의 충전·주유소 공급자가 설정되지 않았습니다."
            )
        now = time.monotonic()
        if self._cached_result is not None and now < self._cache_expires_at:
            return self._cached_result

        result = StationSourceResult(
            stations=self._normalize_stations(self._fetch_items()),
            retrieved_at=datetime.now(UTC).isoformat(),
        )
        validate_station_source_result(self.source_name, self.source_url, result)
        self._cached_result = result
        self._cache_expires_at = now + self._cache_ttl_seconds
        return result


class KpetroHydrogenStationProvider:
    """Combines K-Petro hydrogen station operation and real-time OpenAPIs."""

    source_name = "한국석유관리원 수소충전소 운영·실시간정보"
    source_url = "https://www.data.go.kr/data/15133332/openapi.do"
    realtime_source_url = "https://www.data.go.kr/data/15133338/openapi.do"
    _operation_endpoint = "https://apis.data.go.kr/B552532/h2nbiz_2/operationInfo"
    _realtime_endpoint = "https://apis.data.go.kr/B552532/h2nbiz_3/currentInfo"
    _seoul_timezone = timezone(timedelta(hours=9))
    _pressure_by_charger_type = {
        "01": 350,
        "02": 700,
        "03": 800,
        "04": 300,
    }

    def __init__(
        self,
        service_key: str,
        *,
        timeout_seconds: float = 10.0,
        cache_ttl_seconds: float = 300.0,
        transport: StationJsonTransport | None = None,
    ) -> None:
        normalized_key = unquote(service_key.strip())
        if not normalized_key:
            raise ValueError("K-Petro hydrogen station service key is required")
        if timeout_seconds <= 0:
            raise ValueError("K-Petro hydrogen station timeout must be greater than zero")
        if cache_ttl_seconds < 0:
            raise ValueError("K-Petro hydrogen station cache TTL must not be negative")
        self._service_key = normalized_key
        self._timeout_seconds = timeout_seconds
        self._cache_ttl_seconds = cache_ttl_seconds
        self._transport = transport or _default_station_json_transport
        self._cached_result: StationSourceResult | None = None
        self._cache_expires_at = 0.0

    def _request(self, endpoint: str) -> Mapping[str, Any]:
        params = {"serviceKey": self._service_key}
        return self._transport(
            f"{endpoint}?{urlencode(params)}", self._timeout_seconds
        )

    @staticmethod
    def _items(payload: Mapping[str, Any], label: str) -> list[Mapping[str, Any]]:
        response = payload.get("response")
        root = response if isinstance(response, Mapping) else payload
        header = root.get("header")
        header_mapping = header if isinstance(header, Mapping) else root
        result_code = str(header_mapping.get("resultCode", "")).strip()
        if result_code not in {"0", "00", "0000"}:
            raise StationProviderError(
                f"수소충전소 {label} 공식 API가 요청을 처리하지 못했습니다."
            )

        body = root.get("body")
        body_mapping = body if isinstance(body, Mapping) else root
        items_container = body_mapping.get("items")
        if items_container in (None, ""):
            return []
        raw_items = (
            items_container.get("item", [])
            if isinstance(items_container, Mapping)
            else items_container
        )
        if isinstance(raw_items, Mapping):
            raw_items = [raw_items]
        if not isinstance(raw_items, list) or any(
            not isinstance(item, Mapping) for item in raw_items
        ):
            raise StationProviderError(
                f"수소충전소 {label} 공식 API 목록 형식이 올바르지 않습니다."
            )
        return [item for item in raw_items if isinstance(item, Mapping)]

    @classmethod
    def _parse_observed_at(cls, raw_value: Any) -> str | None:
        value = str(raw_value or "").strip()
        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            observed = datetime.fromisoformat(normalized)
        except ValueError:
            observed = None
        if observed is None:
            for pattern in ("%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    observed = datetime.strptime(value, pattern)
                    break
                except ValueError:
                    continue
        if observed is None:
            return None
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=cls._seoul_timezone)
        return observed.isoformat()

    @staticmethod
    def _non_negative_int(raw_value: Any) -> int | None:
        if raw_value in (None, ""):
            return None
        try:
            value = int(float(raw_value))
        except (TypeError, ValueError):
            return None
        return value if value >= 0 else None

    @staticmethod
    def _non_negative_float(raw_value: Any) -> float | None:
        if raw_value in (None, ""):
            return None
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            return None
        return value if math.isfinite(value) and value >= 0 else None

    @classmethod
    def _status(
        cls,
        operation: Mapping[str, Any],
        realtime: Mapping[str, Any] | None,
    ) -> StationStatus:
        if str(operation.get("oper_yn", "")).strip().upper() == "N":
            return "unavailable"
        if realtime is None:
            return "unknown"

        operation_status = str(realtime.get("oper_sttus_cd", "")).strip()
        pos_status = str(realtime.get("pos_sttus_cd", "")).strip()
        congestion_status = str(realtime.get("cnf_sttus_cd", "")).strip()
        if operation_status in {"10", "20"} or pos_status in {"1", "2", "3", "9"}:
            return "unavailable"
        if operation_status != "30" or pos_status not in {"", "0"}:
            return "unknown"
        queue_count = cls._non_negative_int(realtime.get("wait_vhcle_alge"))
        if congestion_status == "3" or (queue_count is not None and queue_count > 0):
            return "busy"
        if congestion_status in {"1", "2"}:
            return "available"
        return "unknown"

    @classmethod
    def _latest_realtime_by_station(
        cls, items: Sequence[Mapping[str, Any]]
    ) -> dict[str, Mapping[str, Any]]:
        latest: dict[str, Mapping[str, Any]] = {}
        for item in items:
            station_id = str(item.get("chrstn_mno", "")).strip()
            if not station_id:
                continue
            existing = latest.get(station_id)
            if existing is None:
                latest[station_id] = item
                continue
            observed = cls._parse_observed_at(item.get("last_mdfcn_dt")) or ""
            existing_observed = (
                cls._parse_observed_at(existing.get("last_mdfcn_dt")) or ""
            )
            if observed > existing_observed:
                latest[station_id] = item
        return latest

    @classmethod
    def _normalize_stations(
        cls,
        operation_items: Sequence[Mapping[str, Any]],
        realtime_items: Sequence[Mapping[str, Any]],
    ) -> tuple[StationCandidate, ...]:
        realtime_by_station = cls._latest_realtime_by_station(realtime_items)
        stations: list[StationCandidate] = []
        for operation in operation_items:
            station_id = str(operation.get("chrstn_mno", "")).strip()
            if not station_id or str(operation.get("del_at", "N")).strip().upper() == "Y":
                continue
            name = str(operation.get("chrstn_nm", "")).strip()
            address = str(
                operation.get("road_nm_addr") or operation.get("lotno_addr") or ""
            ).strip()
            try:
                longitude = float(operation.get("lon"))
                latitude = float(operation.get("let"))
            except (TypeError, ValueError):
                continue
            if not name or not address or not _finite_coordinate(longitude, latitude):
                continue

            realtime = realtime_by_station.get(station_id)
            charger_type = str(operation.get("chrgr_ty_cd", "")).strip()
            stations.append(
                StationCandidate(
                    station_id=station_id,
                    name=name,
                    address=address,
                    longitude=longitude,
                    latitude=latitude,
                    energy_kind="hydrogen",
                    status=cls._status(operation, realtime),
                    status_observed_at=(
                        cls._parse_observed_at(realtime.get("last_mdfcn_dt"))
                        if realtime is not None
                        else None
                    ),
                    pressure_bar=cls._pressure_by_charger_type.get(charger_type),
                    queue_vehicle_count=(
                        cls._non_negative_int(realtime.get("wait_vhcle_alge"))
                        if realtime is not None
                        else None
                    ),
                    trailer_pressure_bar=(
                        cls._non_negative_float(realtime.get("tt_pressr"))
                        if realtime is not None
                        else None
                    ),
                )
            )
        return tuple(stations)

    def list_stations(self, energy_kind: EnergyKind) -> StationSourceResult:
        if energy_kind != "hydrogen":
            raise StationProviderNotConfiguredError(
                "선택한 동력원의 충전·주유소 공급자가 설정되지 않았습니다."
            )
        now = time.monotonic()
        if self._cached_result is not None and now < self._cache_expires_at:
            return self._cached_result

        operation_items = self._items(
            self._request(self._operation_endpoint), "운영정보"
        )
        realtime_items = self._items(
            self._request(self._realtime_endpoint), "실시간정보"
        )
        result = StationSourceResult(
            stations=self._normalize_stations(operation_items, realtime_items),
            retrieved_at=datetime.now(UTC).isoformat(),
        )
        validate_station_source_result(self.source_name, self.source_url, result)
        self._cached_result = result
        self._cache_expires_at = now + self._cache_ttl_seconds
        return result


class JsonStationProvider:
    """Reads a normalized, source-attributed station snapshot from a local file."""

    def __init__(self, catalog_path: Path) -> None:
        try:
            payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise StationProviderError("로컬 충전·주유소 카탈로그를 읽을 수 없습니다.") from error
        if not isinstance(payload, Mapping):
            raise StationProviderError("로컬 충전·주유소 카탈로그 형식이 올바르지 않습니다.")
        self.source_name = str(payload.get("source_name", "")).strip()
        self.source_url = str(payload.get("source_url", "")).strip()
        self._retrieved_at = str(payload.get("retrieved_at", "")).strip()
        if not self.source_name or not self.source_url or not self._retrieved_at:
            raise StationProviderError("카탈로그의 출처명, 출처 URL, 조회시각이 필요합니다.")
        if not _valid_https_url(self.source_url):
            raise StationProviderError("카탈로그 출처 URL은 HTTPS여야 합니다.")
        raw_stations = payload.get("stations")
        if not isinstance(raw_stations, list):
            raise StationProviderError("카탈로그의 충전·주유소 목록이 필요합니다.")
        self._stations = tuple(self._parse_station(item) for item in raw_stations)

    @staticmethod
    def _parse_station(item: Any) -> StationCandidate:
        if not isinstance(item, Mapping):
            raise StationProviderError("충전·주유소 항목 형식이 올바르지 않습니다.")
        try:
            energy_kind = str(item["energy_kind"])
            status = str(item.get("status", "unknown"))
            if energy_kind not in {"electric", "hydrogen", "fuel"}:
                raise ValueError
            if status not in {"available", "busy", "unavailable", "unknown"}:
                raise ValueError
            fuel_grades_payload = item.get("fuel_grades", [])
            if not isinstance(fuel_grades_payload, list):
                raise ValueError
            station = StationCandidate(
                station_id=str(item["station_id"]).strip(),
                name=str(item["name"]).strip(),
                address=str(item["address"]).strip(),
                longitude=float(item["longitude"]),
                latitude=float(item["latitude"]),
                energy_kind=energy_kind,  # type: ignore[arg-type]
                status=status,  # type: ignore[arg-type]
                status_observed_at=(
                    str(item["status_observed_at"]).strip()
                    if item.get("status_observed_at")
                    else None
                ),
                power_kw=float(item["power_kw"]) if item.get("power_kw") is not None else None,
                pressure_bar=int(item["pressure_bar"]) if item.get("pressure_bar") is not None else None,
                queue_vehicle_count=(
                    int(item["queue_vehicle_count"])
                    if item.get("queue_vehicle_count") is not None
                    else None
                ),
                trailer_pressure_bar=(
                    float(item["trailer_pressure_bar"])
                    if item.get("trailer_pressure_bar") is not None
                    else None
                ),
                fuel_grades=tuple(str(grade).strip() for grade in fuel_grades_payload),
                source_url=str(item["source_url"]).strip() if item.get("source_url") else None,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise StationProviderError("충전·주유소 항목 값을 확인할 수 없습니다.") from error
        if not station.station_id or not station.name or not station.address:
            raise StationProviderError("충전·주유소 식별자, 이름, 주소가 필요합니다.")
        if not _finite_coordinate(station.longitude, station.latitude):
            raise StationProviderError("충전·주유소 좌표가 유효하지 않습니다.")
        return station

    def list_stations(self, energy_kind: EnergyKind) -> StationSourceResult:
        result = StationSourceResult(
            stations=tuple(
                station for station in self._stations if station.energy_kind == energy_kind
            ),
            retrieved_at=self._retrieved_at,
        )
        validate_station_source_result(self.source_name, self.source_url, result)
        return result
