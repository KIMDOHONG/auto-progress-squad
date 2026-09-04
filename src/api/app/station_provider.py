from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.parse import urlparse


EnergyKind = Literal["electric", "hydrogen", "fuel"]
StationStatus = Literal["available", "busy", "unavailable", "unknown"]
FuelGradeMatch = Literal["confirmed", "unknown", "not-applicable"]


class StationProviderError(Exception):
    """Raised when station data cannot be returned or safely interpreted."""


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


class StationProvider(Protocol):
    source_name: str
    source_url: str

    def list_stations(self, energy_kind: EnergyKind) -> StationSourceResult: ...


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


def _route_distance(
    route_path: Sequence[tuple[float, float]], station: StationCandidate
) -> tuple[float, float]:
    reference_latitude = sum(point[1] for point in route_path) / len(route_path)
    projected_route = [
        _project_km(longitude, latitude, reference_latitude)
        for longitude, latitude in route_path
    ]
    point_x, point_y = _project_km(
        station.longitude, station.latitude, reference_latitude
    )
    segment_lengths = [
        math.hypot(end_x - start_x, end_y - start_y)
        for (start_x, start_y), (end_x, end_y) in zip(
            projected_route, projected_route[1:]
        )
    ]
    route_length = sum(segment_lengths)
    if route_length <= 0:
        raise StationProviderError("경로 좌표가 서로 다른 두 지점을 포함해야 합니다.")

    best_distance = math.inf
    best_progress = 0.0
    traversed = 0.0
    for index, ((start_x, start_y), (end_x, end_y)) in enumerate(
        zip(projected_route, projected_route[1:])
    ):
        delta_x = end_x - start_x
        delta_y = end_y - start_y
        segment_length = segment_lengths[index]
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
            best_progress = (traversed + ratio * segment_length) / route_length * 100
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

    normalized_fuel_grade = fuel_grade.strip().lower() if fuel_grade else None
    ranked: list[RankedStation] = []
    for station in stations:
        if station.energy_kind != energy_kind:
            continue
        if not _finite_coordinate(station.longitude, station.latitude):
            raise StationProviderError("충전·주유소 좌표가 유효하지 않습니다.")

        fuel_grade_match: FuelGradeMatch = "not-applicable"
        if energy_kind == "fuel" and normalized_fuel_grade:
            normalized_grades = {grade.strip().lower() for grade in station.fuel_grades}
            if normalized_grades:
                if normalized_fuel_grade not in normalized_grades:
                    continue
                fuel_grade_match = "confirmed"
            else:
                fuel_grade_match = "unknown"

        distance, progress = _route_distance(route_path, station)
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
