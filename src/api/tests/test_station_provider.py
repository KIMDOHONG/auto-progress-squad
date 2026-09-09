from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.station_provider import (
    JsonStationProvider,
    KecoEvChargerProvider,
    KpetroHydrogenStationProvider,
    OpinetFuelStationProvider,
    StationCandidate,
    StationProviderError,
    StationProviderNotConfiguredError,
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


def test_station_search_endpoint_returns_hydrogen_realtime_details(
    tmp_path: Path,
) -> None:
    station = StationCandidate(
        station_id="h2-1",
        name="테스트 수소충전소",
        address="부산 테스트로 1",
        longitude=129.05,
        latitude=35.002,
        energy_kind="hydrogen",
        status="busy",
        status_observed_at="2026-09-04T10:00:00+09:00",
        pressure_bar=700,
        queue_vehicle_count=2,
        trailer_pressure_bar=132.4,
    )
    provider = FakeStationProvider((station,))
    with TestClient(
        create_app(settings(tmp_path), station_provider=provider)
    ) as client:
        response = client.post(
            "/api/v1/planner/stations",
            json={
                "energy_kind": "hydrogen",
                "route_path": [
                    {"longitude": longitude, "latitude": latitude}
                    for longitude, latitude in ROUTE_PATH
                ],
                "corridor_km": 2,
            },
        )

    assert response.status_code == 200
    result = response.json()["stations"][0]
    assert result["pressure_bar"] == 700
    assert result["queue_vehicle_count"] == 2
    assert result["trailer_pressure_bar"] == 132.4


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


def official_payload(
    items: list[dict[str, object]], total_count: int
) -> dict[str, object]:
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {"items": {"item": items}, "totalCount": total_count},
        }
    }


def test_keco_provider_paginates_normalizes_and_caches_chargers() -> None:
    requested_queries: list[dict[str, list[str]]] = []

    def transport(url: str, timeout_seconds: float) -> dict[str, object]:
        assert timeout_seconds == 3.5
        query = parse_qs(urlparse(url).query)
        requested_queries.append(query)
        assert query["serviceKey"] == ["abc+123/="]
        assert query["zcode"] == ["26"]
        assert query["numOfRows"] == ["10"]
        if query["pageNo"] == ["1"]:
            return official_payload(
                [
                    {
                        "statId": "ME001",
                        "chgerId": "01",
                        "statNm": "테스트 충전소",
                        "addr": "부산광역시 동구 중앙대로 200",
                        "addrDetail": "지하 1층",
                        "lat": "35.1149",
                        "lng": "129.0414",
                        "stat": "3",
                        "statUpdDt": "20260904090000",
                        "output": "50",
                        "delYn": "N",
                    },
                    {
                        "statId": "ME001",
                        "chgerId": "02",
                        "statNm": "테스트 충전소",
                        "addr": "부산광역시 동구 중앙대로 200",
                        "addrDetail": "지하 1층",
                        "lat": "35.1149",
                        "lng": "129.0414",
                        "stat": "2",
                        "statUpdDt": "20260904100000",
                        "output": "200",
                        "delYn": "N",
                    },
                    *[
                        {"statId": f"deleted-{index}", "delYn": "Y"}
                        for index in range(8)
                    ],
                ],
                11,
            )
        return official_payload(
            [
                {
                    "statId": "ME002",
                    "chgerId": "01",
                    "statNm": "두 번째 충전소",
                    "addr": "부산광역시 부산진구 테스트로 2",
                    "lat": "35.16",
                    "lng": "129.06",
                    "stat": "5",
                    "statUpdDt": "invalid",
                    "output": "100",
                }
            ],
            11,
        )

    provider = KecoEvChargerProvider(
        "abc%2B123%2F%3D",
        timeout_seconds=3.5,
        cache_ttl_seconds=1_800,
        page_size=10,
        region_codes=("26",),
        transport=transport,
    )

    first = provider.list_stations("electric")
    second = provider.list_stations("electric")

    assert second is first
    assert len(requested_queries) == 2
    assert [query["pageNo"] for query in requested_queries] == [["1"], ["2"]]
    assert [station.station_id for station in first.stations] == ["ME001", "ME002"]
    assert first.stations[0].address == "부산광역시 동구 중앙대로 200 지하 1층"
    assert first.stations[0].status == "available"
    assert first.stations[0].status_observed_at == "2026-09-04T10:00:00+09:00"
    assert first.stations[0].power_kw == 200
    assert first.stations[1].status == "unavailable"
    assert first.stations[1].status_observed_at is None


def test_keco_provider_rejects_unsupported_energy_kind() -> None:
    provider = KecoEvChargerProvider(
        "test-key", transport=lambda url, timeout: official_payload([], 0)
    )

    with pytest.raises(StationProviderNotConfiguredError):
        provider.list_stations("hydrogen")


def test_keco_provider_reports_official_api_failure() -> None:
    provider = KecoEvChargerProvider(
        "test-key",
        transport=lambda url, timeout: {
            "response": {
                "header": {
                    "resultCode": "30",
                    "resultMsg": "SERVICE KEY IS NOT REGISTERED",
                },
                "body": {},
            }
        },
    )

    with pytest.raises(StationProviderError):
        provider.list_stations("electric")


def hydrogen_payload(items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
        "body": {"items": {"item": items}, "totalCount": len(items)},
    }


def opinet_payload(items: list[dict[str, object]]) -> dict[str, object]:
    return {"RESULT": {"OIL": items}}


def test_opinet_provider_combines_route_radius_and_station_detail() -> None:
    requested: list[tuple[str, dict[str, list[str]]]] = []
    longitude, latitude = OpinetFuelStationProvider._from_katec.transform(
        314871.8, 544012.0
    )

    def transport(url: str, timeout_seconds: float) -> dict[str, object]:
        assert timeout_seconds == 4.0
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        requested.append((parsed.path, query))
        assert query["certkey"] == ["abc+123/="]
        if parsed.path.endswith("/aroundAll.do"):
            assert query["prodcd"] == ["B034"]
            assert query["radius"] == ["5000"]
            return opinet_payload(
                [
                    {
                        "UNI_ID": "A0010207",
                        "OS_NM": "SK서광주유소",
                        "PRICE": "1920",
                        "GIS_X_COOR": "314871.8",
                        "GIS_Y_COOR": "544012.0",
                    }
                ]
            )
        return opinet_payload(
            [
                {
                    "UNI_ID": "A0010207",
                    "OS_NM": "SK서광주유소",
                    "NEW_ADR": "서울 강남구 역삼로 142",
                    "GIS_X_COOR": "314871.8",
                    "GIS_Y_COOR": "544012.0",
                    "OIL_PRICE": [
                        {
                            "PRODCD": "B034",
                            "PRICE": "1920",
                            "TRADE_DT": "20250723",
                            "TRADE_TM": "145312",
                        }
                    ],
                }
            ]
        )

    provider = OpinetFuelStationProvider(
        "abc%2B123%2F%3D",
        timeout_seconds=4.0,
        max_sample_points=2,
        transport=transport,
    )
    result = provider.list_stations_near_route(
        ((longitude - 0.01, latitude), (longitude + 0.01, latitude)),
        corridor_km=5,
        limit=5,
        fuel_grade="premium",
    )

    assert len(result.stations) == 1
    station = result.stations[0]
    assert station.station_id == "A0010207"
    assert station.address == "서울 강남구 역삼로 142"
    assert station.fuel_grades == ("premium",)
    assert station.fuel_price_per_liter == 1920
    assert station.status == "unknown"
    assert station.status_observed_at is None
    assert station.fuel_price_observed_at == "2025-07-23T14:53:12+09:00"
    assert [path for path, _ in requested].count("/api/aroundAll.do") == 2
    assert [path for path, _ in requested].count("/api/detailById.do") == 1


def test_opinet_provider_does_not_infer_unpublished_special_fuel_grade() -> None:
    longitude, latitude = OpinetFuelStationProvider._from_katec.transform(
        314871.8, 544012.0
    )

    def transport(url: str, timeout_seconds: float) -> dict[str, object]:
        del timeout_seconds
        path = urlparse(url).path
        if path.endswith("/aroundAll.do"):
            return opinet_payload(
                [
                    {
                        "UNI_ID": "A0010207",
                        "OS_NM": "SK서광주유소",
                        "PRICE": "1920",
                        "GIS_X_COOR": "314871.8",
                        "GIS_Y_COOR": "544012.0",
                    }
                ]
            )
        return opinet_payload(
            [
                {
                    "UNI_ID": "A0010207",
                    "OS_NM": "SK서광주유소",
                    "NEW_ADR": "서울 강남구 역삼로 142",
                    "GIS_X_COOR": "314871.8",
                    "GIS_Y_COOR": "544012.0",
                }
            ]
        )

    provider = OpinetFuelStationProvider(
        "test-key", max_sample_points=2, transport=transport
    )
    result = provider.list_stations_near_route(
        ((longitude - 0.01, latitude), (longitude + 0.01, latitude)),
        corridor_km=5,
        limit=5,
        fuel_grade="super-premium",
    )

    assert result.stations[0].fuel_grades == ()
    assert result.stations[0].fuel_price_per_liter is None
    assert result.stations[0].fuel_price_observed_at is None


def test_kpetro_provider_combines_operation_and_latest_realtime_data() -> None:
    requested_paths: list[str] = []

    def transport(url: str, timeout_seconds: float) -> dict[str, object]:
        assert timeout_seconds == 4.0
        parsed = urlparse(url)
        requested_paths.append(parsed.path)
        assert parse_qs(parsed.query)["serviceKey"] == ["abc+123/="]
        if parsed.path.endswith("/operationInfo.do"):
            return hydrogen_payload(
                [
                    {
                        "chrstn_mno": "H2001",
                        "chrstn_nm": "테스트 수소충전소",
                        "road_nm_addr": "부산광역시 동구 중앙대로 200",
                        "lotno_addr": "부산광역시 동구 초량동 1",
                        "lon": "129.0414",
                        "let": "35.1149",
                        "chrgr_ty_cd": "02",
                        "oper_yn": "Y",
                        "del_at": "N",
                    },
                    {
                        "chrstn_mno": "H2002",
                        "chrstn_nm": "영업중지 충전소",
                        "road_nm_addr": "부산광역시 동구 테스트로 2",
                        "lon": "129.05",
                        "let": "35.12",
                        "chrgr_ty_cd": "01",
                        "oper_yn": "N",
                        "del_at": "N",
                    },
                    {"chrstn_mno": "deleted", "del_at": "Y"},
                ]
            )
        return hydrogen_payload(
            [
                {
                    "chrstn_mno": "H2001",
                    "last_mdfcn_dt": "2026-09-04 09:00:00",
                    "tt_pressr": 140.5,
                    "wait_vhcle_alge": 0,
                    "cnf_sttus_cd": "1",
                    "oper_sttus_cd": "30",
                    "pos_sttus_cd": "0",
                },
                {
                    "chrstn_mno": "H2001",
                    "last_mdfcn_dt": "2026-09-04 10:00:00",
                    "tt_pressr": 132.4,
                    "wait_vhcle_alge": 2,
                    "cnf_sttus_cd": "3",
                    "oper_sttus_cd": "30",
                    "pos_sttus_cd": "0",
                },
            ]
        )

    provider = KpetroHydrogenStationProvider(
        "abc%2B123%2F%3D",
        timeout_seconds=4.0,
        cache_ttl_seconds=300,
        transport=transport,
    )

    first = provider.list_stations("hydrogen")
    second = provider.list_stations("hydrogen")

    assert second is first
    assert requested_paths == [
        "/api/openData/chrstnList/operationInfo.do",
        "/api/openData/chrstnList/currentInfo.do",
    ]
    assert [station.station_id for station in first.stations] == ["H2001", "H2002"]
    station = first.stations[0]
    assert station.address == "부산광역시 동구 중앙대로 200"
    assert station.status == "busy"
    assert station.status_observed_at == "2026-09-04T10:00:00+09:00"
    assert station.pressure_bar == 700
    assert station.queue_vehicle_count == 2
    assert station.trailer_pressure_bar == 132.4
    assert first.stations[1].status == "unavailable"
    assert first.stations[1].status_observed_at is None


def test_kpetro_provider_maps_official_status_codes_conservatively() -> None:
    operation = {"oper_yn": "Y"}

    assert KpetroHydrogenStationProvider._status(operation, None) == "unknown"
    assert KpetroHydrogenStationProvider._status(
        operation,
        {"oper_sttus_cd": "30", "pos_sttus_cd": "0", "cnf_sttus_cd": "1"},
    ) == "available"
    assert KpetroHydrogenStationProvider._status(
        operation,
        {"oper_sttus_cd": "30", "pos_sttus_cd": "0", "cnf_sttus_cd": "0"},
    ) == "unknown"
    assert KpetroHydrogenStationProvider._status(
        operation,
        {"oper_sttus_cd": "30", "pos_sttus_cd": "3", "cnf_sttus_cd": "1"},
    ) == "unavailable"
    assert KpetroHydrogenStationProvider._status(
        operation,
        {"oper_sttus_cd": "20", "pos_sttus_cd": "0", "cnf_sttus_cd": "1"},
    ) == "unavailable"


def test_kpetro_provider_rejects_unsupported_kind_and_api_failure() -> None:
    provider = KpetroHydrogenStationProvider(
        "test-key", transport=lambda url, timeout: hydrogen_payload([])
    )
    with pytest.raises(StationProviderNotConfiguredError):
        provider.list_stations("electric")

    failed = KpetroHydrogenStationProvider(
        "test-key",
        transport=lambda url, timeout: {
            "header": {"resultCode": "30", "resultMsg": "SERVICE KEY ERROR"},
            "body": {},
        },
    )
    with pytest.raises(StationProviderError, match=r"resultCode=30"):
        failed.list_stations("hydrogen")


def test_kpetro_provider_falls_back_when_direct_endpoint_rejects_request() -> None:
    requested_paths: list[str] = []

    def transport(url: str, timeout_seconds: float) -> dict[str, object]:
        del timeout_seconds
        path = urlparse(url).path
        requested_paths.append(path)
        if path.startswith("/api/openData/"):
            return {
                "header": {"resultCode": "01", "resultMsg": "INVALID KEY"},
                "body": {},
            }
        return hydrogen_payload([])

    provider = KpetroHydrogenStationProvider("test-key", transport=transport)

    assert provider.list_stations("hydrogen").stations == ()
    assert requested_paths == [
        "/api/openData/chrstnList/operationInfo.do",
        "/B552532/h2nbiz_2/operationInfo",
        "/api/openData/chrstnList/currentInfo.do",
        "/B552532/h2nbiz_3/currentInfo",
    ]


def test_kpetro_provider_falls_back_to_public_data_gateway() -> None:
    requested_paths: list[str] = []

    def transport(url: str, timeout_seconds: float) -> dict[str, object]:
        del timeout_seconds
        path = urlparse(url).path
        requested_paths.append(path)
        if path.startswith("/api/openData/"):
            raise StationProviderError("direct endpoint unavailable")
        return hydrogen_payload([])

    provider = KpetroHydrogenStationProvider("test-key", transport=transport)

    assert provider.list_stations("hydrogen").stations == ()
    assert requested_paths == [
        "/api/openData/chrstnList/operationInfo.do",
        "/B552532/h2nbiz_2/operationInfo",
        "/api/openData/chrstnList/currentInfo.do",
        "/B552532/h2nbiz_3/currentInfo",
    ]


def test_official_providers_are_created_independently_from_settings(
    tmp_path: Path,
) -> None:
    configured = Settings(
        database_path=tmp_path / "stations.db",
        cors_origins=("https://kimdohong.github.io",),
        manual_source_dir=tmp_path / "manuals",
        ev_charger_service_key="test-key",
        ev_charger_region_codes=("26",),
        hydrogen_station_service_key="test-key",
        opinet_service_key="test-key",
    )
    with TestClient(create_app(configured)) as client:
        assert client.app.state.station_provider is None
        assert isinstance(
            client.app.state.station_providers["electric"], KecoEvChargerProvider
        )
        assert isinstance(
            client.app.state.station_providers["hydrogen"],
            KpetroHydrogenStationProvider,
        )
        assert isinstance(
            client.app.state.station_providers["fuel"], OpinetFuelStationProvider
        )
        response = client.post(
            "/api/v1/planner/stations",
            json={
                "energy_kind": "fuel",
                "route_path": [
                    {"longitude": longitude, "latitude": latitude}
                    for longitude, latitude in ROUTE_PATH
                ],
            },
        )

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "station_source_not_configured",
        "message": "선택한 동력원의 충전·주유소 데이터 공급자가 설정되지 않았습니다.",
        "retryable": False,
        "details": None,
    }
