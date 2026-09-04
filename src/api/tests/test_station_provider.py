from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.station_provider import (
    JsonStationProvider,
    StationCandidate,
    StationProviderError,
    StationSourceResult,
    rank_route_stations,
)


ROUTE_PATH = ((129.0, 35.0), (129.1, 35.0))


def candidate(
    station_id: str,
    *,
    longitude: float,
    latitude: float,
    energy_kind: str = "electric",
    fuel_grades: tuple[str, ...] = (),
    observed: str | None = "2026-09-04T00:00:00+00:00",
) -> StationCandidate:
    return StationCandidate(
        station_id=station_id,
        name=f"테스트 {station_id}",
        address=f"부산 테스트로 {station_id}",
        longitude=longitude,
        latitude=latitude,
        energy_kind=energy_kind,  # type: ignore[arg-type]
        status="available",
        status_observed_at=observed,
        power_kw=200 if energy_kind == "electric" else None,
        pressure_bar=700 if energy_kind == "hydrogen" else None,
        fuel_grades=fuel_grades,
    )


class FakeStationProvider:
    source_name = "평가용 공식 데이터 스냅샷"
    source_url = "https://example.go.kr/stations"

    def __init__(self, stations: Sequence[StationCandidate]) -> None:
        self.stations = tuple(stations)
        self.requested_kinds: list[str] = []

    def list_stations(self, energy_kind: str) -> StationSourceResult:
        self.requested_kinds.append(energy_kind)
        return StationSourceResult(
            stations=self.stations,
            retrieved_at="2026-09-04T00:05:00+00:00",
        )


class FailingStationProvider(FakeStationProvider):
    def list_stations(self, energy_kind: str) -> StationSourceResult:
        raise StationProviderError("upstream unavailable")


class UnattributedStationProvider(FakeStationProvider):
    source_url = "http://example.go.kr/stations"


def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "stations.db",
        cors_origins=("https://kimdohong.github.io",),
        manual_source_dir=tmp_path / "manuals",
    )


def test_rank_route_stations_filters_corridor_and_orders_by_distance() -> None:
    ranked = rank_route_stations(
        ROUTE_PATH,
        (
            candidate("far", longitude=129.05, latitude=35.1),
            candidate("near", longitude=129.05, latitude=35.002),
            candidate("next", longitude=129.08, latitude=35.01),
            candidate(
                "wrong-kind",
                longitude=129.05,
                latitude=35.001,
                energy_kind="hydrogen",
            ),
        ),
        energy_kind="electric",
        corridor_km=2,
        limit=5,
    )

    assert [item.station.station_id for item in ranked] == ["near", "next"]
    assert ranked[0].distance_to_route_km == 0.22
    assert 49 < ranked[0].route_progress_percent < 51


def test_rank_route_stations_keeps_unknown_fuel_grade_but_rejects_known_mismatch() -> None:
    ranked = rank_route_stations(
        ROUTE_PATH,
        (
            candidate(
                "confirmed",
                longitude=129.03,
                latitude=35.001,
                energy_kind="fuel",
                fuel_grades=("premium",),
            ),
            candidate(
                "unknown",
                longitude=129.04,
                latitude=35.001,
                energy_kind="fuel",
            ),
            candidate(
                "mismatch",
                longitude=129.05,
                latitude=35.001,
                energy_kind="fuel",
                fuel_grades=("diesel",),
            ),
        ),
        energy_kind="fuel",
        corridor_km=2,
        limit=5,
        fuel_grade="premium",
    )

    assert {item.station.station_id for item in ranked} == {"confirmed", "unknown"}
    assert {
        item.station.station_id: item.fuel_grade_match for item in ranked
    } == {"confirmed": "confirmed", "unknown": "unknown"}


def test_station_search_endpoint_returns_ranked_candidates_and_warnings(
    tmp_path: Path,
) -> None:
    provider = FakeStationProvider(
        (
            candidate("ev-1", longitude=129.05, latitude=35.002),
            candidate(
                "ev-2", longitude=129.08, latitude=35.01, observed=None
            ),
        )
    )
    with TestClient(
        create_app(settings(tmp_path), station_provider=provider)
    ) as client:
        response = client.post(
            "/api/v1/planner/stations",
            json={
                "energy_kind": "electric",
                "route_path": [
                    {"longitude": longitude, "latitude": latitude}
                    for longitude, latitude in ROUTE_PATH
                ],
                "corridor_km": 2,
                "limit": 5,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "matched"
    assert [item["station_id"] for item in payload["stations"]] == ["ev-1", "ev-2"]
    assert payload["stations"][0]["power_kw"] == 200
    assert payload["source_name"] == provider.source_name
    assert payload["retrieved_at"] == "2026-09-04T00:05:00+00:00"
    assert payload["warnings"] == [
        "표시된 상태에는 충전·주유 대기시간이 포함되지 않습니다.",
        "상태 조회시각이 없는 후보는 현재 이용 가능 여부를 직접 확인해야 합니다.",
    ]
    assert provider.requested_kinds == ["electric"]


def test_station_search_endpoint_distinguishes_unconfigured_empty_and_failed(
    tmp_path: Path,
) -> None:
    request = {
        "energy_kind": "hydrogen",
        "route_path": [
            {"longitude": longitude, "latitude": latitude}
            for longitude, latitude in ROUTE_PATH
        ],
    }
    with TestClient(create_app(settings(tmp_path))) as client:
        unconfigured = client.post("/api/v1/planner/stations", json=request)
    assert unconfigured.status_code == 503
    assert unconfigured.json()["error"]["code"] == "station_source_not_configured"

    with TestClient(
        create_app(settings(tmp_path), station_provider=FakeStationProvider(()))
    ) as client:
        empty = client.post("/api/v1/planner/stations", json=request)
    assert empty.status_code == 200
    assert empty.json()["status"] == "no_results"
    assert empty.json()["stations"] == []

    with TestClient(
        create_app(settings(tmp_path), station_provider=FailingStationProvider(()))
    ) as client:
        failed = client.post("/api/v1/planner/stations", json=request)
    assert failed.status_code == 503
    assert failed.json()["error"] == {
        "code": "station_source_unavailable",
        "message": "충전·주유소 후보를 확인할 수 없습니다. 잠시 후 다시 시도해 주세요.",
        "retryable": True,
        "details": None,
    }

    with TestClient(
        create_app(
            settings(tmp_path), station_provider=UnattributedStationProvider(())
        )
    ) as client:
        unattributed = client.post("/api/v1/planner/stations", json=request)
    assert unattributed.status_code == 503
    assert unattributed.json()["error"]["code"] == "station_source_unavailable"


def test_json_station_provider_loads_source_attributed_local_snapshot(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "stations.json"
    catalog.write_text(
        json.dumps(
            {
                "source_name": "공식 데이터 내보내기",
                "source_url": "https://example.go.kr/openapi",
                "retrieved_at": "2026-09-04T01:00:00+00:00",
                "stations": [
                    {
                        "station_id": "h2-1",
                        "name": "테스트 수소충전소",
                        "address": "부산 테스트로 1",
                        "longitude": 129.05,
                        "latitude": 35.002,
                        "energy_kind": "hydrogen",
                        "status": "available",
                        "status_observed_at": "2026-09-04T00:59:00+00:00",
                        "pressure_bar": 700,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    provider = JsonStationProvider(catalog)
    result = provider.list_stations("hydrogen")

    assert provider.source_name == "공식 데이터 내보내기"
    assert result.retrieved_at == "2026-09-04T01:00:00+00:00"
    assert result.stations[0].pressure_bar == 700
