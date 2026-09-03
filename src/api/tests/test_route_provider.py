from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.route_provider import (
    NaverMapsRouteProvider,
    RouteAlternative,
    RouteCoordinate,
    RouteLocation,
    RouteLocationNotFoundError,
    RouteLookup,
    RouteProviderError,
)


def test_naver_provider_geocodes_both_addresses_and_reads_fast_route() -> None:
    calls: list[tuple[str, dict[str, str], float]] = []

    def transport(url: str, headers: dict[str, str], timeout: float):
        calls.append((url, headers, timeout))
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if "map-geocode" in parsed.path:
            if query["query"] == ["부산역"]:
                return {"addresses": [{"roadAddress": "부산 동구 중앙대로 206", "x": "129.0403", "y": "35.1151"}]}
            return {"addresses": [{"jibunAddress": "부산 남구 용당동 546-2", "x": "129.0964", "y": "35.1266"}]}
        return {"route": {
            "trafast": [{
                "summary": {"distance": 12654, "duration": 1_234_567, "tollFare": 1200, "fuelPrice": 1800},
                "path": [[129.0403, 35.1151], [129.06, 35.12], [129.0964, 35.1266]],
            }],
            "traoptimal": [{
                "summary": {"distance": 13000, "duration": 1_300_000, "tollFare": 0, "fuelPrice": 1900},
                "path": [[129.0403, 35.1151], [129.07, 35.13], [129.0964, 35.1266]],
            }],
        }}

    provider = NaverMapsRouteProvider(
        "client-id", "client-secret", timeout_seconds=3.5, transport=transport
    )
    result = provider.lookup_route("부산역", "부산인력개발원")

    assert result.distance_meters == 12654
    assert result.duration_milliseconds == 1_234_567
    assert result.route_option == "trafast"
    assert result.toll_fare == 1200
    assert len(result.path) == 3
    assert len(result.alternatives) == 2
    assert result.departure.address == "부산 동구 중앙대로 206"
    assert result.destination.address == "부산 남구 용당동 546-2"
    assert len(calls) == 3
    assert parse_qs(urlparse(calls[2][0]).query) == {
        "start": ["129.0403,35.1151"],
        "goal": ["129.0964,35.1266"],
        "option": ["trafast:traoptimal:traavoidtoll"],
        "cartype": ["1"],
        "lang": ["ko"],
    }
    assert calls[0][1]["x-ncp-apigw-api-key-id"] == "client-id"
    assert calls[0][1]["x-ncp-apigw-api-key"] == "client-secret"
    assert calls[0][2] == 3.5


def test_naver_provider_does_not_guess_an_unknown_address() -> None:
    provider = NaverMapsRouteProvider(
        "client-id",
        "client-secret",
        transport=lambda _url, _headers, _timeout: {"addresses": []},
    )

    try:
        provider.lookup_route("없는 출발지", "부산역")
    except RouteLocationNotFoundError as error:
        assert error.field == "departure"
    else:
        raise AssertionError("unknown departure must fail")


def test_naver_provider_uses_confirmed_coordinates_without_geocoding_again() -> None:
    calls: list[str] = []

    def transport(url: str, _headers: dict[str, str], _timeout: float):
        calls.append(url)
        assert "map-geocode" not in url
        return {"route": {
            "trafast": [{
                "summary": {"distance": 5000, "duration": 600_000},
                "path": [[129.04, 35.11], [129.09, 35.12]],
            }],
        }}

    provider = NaverMapsRouteProvider(
        "client-id", "client-secret", transport=transport
    )
    departure = RouteLocation("현재 위치", "확인된 출발지", 129.04, 35.11)
    destination = RouteLocation("청학남로 48", "확인된 목적지", 129.09, 35.12)

    result = provider.lookup_route(departure, destination)

    assert result.departure is departure
    assert result.destination is destination
    assert len(calls) == 1
    assert "map-direction" in calls[0]


def test_naver_provider_reverse_geocodes_gps_coordinates() -> None:
    def transport(url: str, _headers: dict[str, str], _timeout: float):
        query = parse_qs(urlparse(url).query)
        assert query["coords"] == ["129.0689,35.0912"]
        assert query["orders"] == ["roadaddr,addr,admcode,legalcode"]
        return {
            "results": [
                {
                    "region": {
                        "area1": {"name": "부산광역시"},
                        "area2": {"name": "영도구"},
                        "area3": {"name": "청학동"},
                        "area4": {"name": ""},
                    },
                    "land": {
                        "name": "태종로",
                        "number1": "423",
                        "number2": "",
                        "addition0": {"value": "부산시설공단"},
                    },
                }
            ]
        }

    provider = NaverMapsRouteProvider(
        "client-id", "client-secret", transport=transport
    )

    result = provider.reverse_location(129.0689, 35.0912)

    assert result.query == "현재 위치"
    assert result.address == "부산광역시 영도구 청학동 태종로 423 부산시설공단"
    assert result.longitude == 129.0689
    assert result.latitude == 35.0912


class FakeRouteProvider:
    source_name = "검증 경로 공급자"
    source_url = "https://example.com/routes"

    def resolve_location(self, query: str, field: str = "location") -> RouteLocation:
        if field == "departure":
            return RouteLocation(query, "부산 동구 중앙대로 206", 129.0403, 35.1151)
        return RouteLocation(query, "부산 남구 용당동 546-2", 129.0964, 35.1266)

    def reverse_location(self, longitude: float, latitude: float) -> RouteLocation:
        return RouteLocation("현재 위치", "부산 영도구 태종로 423", longitude, latitude)

    def lookup_route(
        self, departure: str | RouteLocation, destination: str | RouteLocation
    ) -> RouteLookup:
        fast = RouteAlternative(
            route_option="trafast",
            distance_meters=12_654,
            duration_milliseconds=1_234_567,
            toll_fare=1_200,
            fuel_price=1_800,
            path=(RouteCoordinate(129.0403, 35.1151), RouteCoordinate(129.0964, 35.1266)),
        )
        optimal = RouteAlternative(
            route_option="traoptimal",
            distance_meters=13_000,
            duration_milliseconds=1_300_000,
            toll_fare=0,
            fuel_price=1_900,
            path=(RouteCoordinate(129.0403, 35.1151), RouteCoordinate(129.0964, 35.1266)),
        )
        resolved_departure = departure if isinstance(departure, RouteLocation) else RouteLocation(
            departure, "부산 동구 중앙대로 206", 129.0403, 35.1151
        )
        resolved_destination = destination if isinstance(destination, RouteLocation) else RouteLocation(
            destination, "부산 남구 용당동 546-2", 129.0964, 35.1266
        )
        return RouteLookup(
            departure=resolved_departure,
            destination=resolved_destination,
            distance_meters=12_654,
            duration_milliseconds=1_234_567,
            route_option="trafast",
            toll_fare=1_200,
            fuel_price=1_800,
            path=fast.path,
            alternatives=(fast, optimal),
        )


class FailingRouteProvider(FakeRouteProvider):
    def lookup_route(self, departure: str, destination: str) -> RouteLookup:
        raise RouteProviderError("upstream failed")


class MissingDestinationProvider(FakeRouteProvider):
    def lookup_route(self, departure: str, destination: str) -> RouteLookup:
        raise RouteLocationNotFoundError("destination")


def make_client(
    tmp_path: Path, provider: object, *, browser_client_id: str | None = None
) -> TestClient:
    settings = Settings(
        database_path=tmp_path / "route-test.db",
        cors_origins=("http://127.0.0.1:5173",),
        manual_source_dir=tmp_path / "manuals",
        naver_maps_browser_client_id=browser_client_id,
    )
    return TestClient(create_app(settings, route_provider=provider))  # type: ignore[arg-type]


def test_route_endpoint_returns_distance_duration_and_resolved_addresses(tmp_path: Path) -> None:
    with make_client(tmp_path, FakeRouteProvider()) as client:
        response = client.post(
            "/api/v1/planner/route",
            json={"departure": "부산역", "destination": "부산인력개발원"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["distance_km"] == 12.7
    assert payload["duration_minutes"] == 21
    assert payload["route_option"] == "trafast"
    assert payload["toll_fare"] == 1200
    assert len(payload["path"]) == 2
    assert [item["route_option"] for item in payload["alternatives"]] == ["trafast", "traoptimal"]
    assert payload["source_name"] == "검증 경로 공급자"
    assert payload["departure"]["query"] == "부산역"
    assert payload["destination"]["address"] == "부산 남구 용당동 546-2"
    assert payload["retrieved_at"]


def test_route_endpoint_uses_coordinates_from_confirmed_locations(tmp_path: Path) -> None:
    with make_client(tmp_path, FakeRouteProvider()) as client:
        response = client.post(
            "/api/v1/planner/route",
            json={
                "departure": "확인된 출발지",
                "destination": "확인된 목적지",
                "departure_location": {
                    "query": "현재 위치",
                    "address": "확인된 출발지",
                    "longitude": 129.04,
                    "latitude": 35.11,
                },
                "destination_location": {
                    "query": "청학남로 48",
                    "address": "확인된 목적지",
                    "longitude": 129.09,
                    "latitude": 35.12,
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["departure"]["query"] == "현재 위치"
    assert payload["departure"]["longitude"] == 129.04
    assert payload["destination"]["query"] == "청학남로 48"


def test_location_resolve_endpoint_requires_an_exact_provider_result(tmp_path: Path) -> None:
    with make_client(tmp_path, FakeRouteProvider()) as client:
        response = client.post(
            "/api/v1/planner/location/resolve",
            json={"query": "부산역", "field": "departure"},
        )

    assert response.status_code == 200
    assert response.json()["location"]["address"] == "부산 동구 중앙대로 206"


def test_reverse_location_endpoint_returns_the_gps_address(tmp_path: Path) -> None:
    with make_client(tmp_path, FakeRouteProvider()) as client:
        response = client.post(
            "/api/v1/planner/location/reverse",
            json={"longitude": 129.0689, "latitude": 35.0912},
        )

    assert response.status_code == 200
    assert response.json()["location"]["query"] == "현재 위치"
    assert response.json()["location"]["address"] == "부산 영도구 태종로 423"


def test_map_config_exposes_only_the_browser_key(tmp_path: Path) -> None:
    with make_client(
        tmp_path, FakeRouteProvider(), browser_client_id="browser-map-id"
    ) as client:
        response = client.get("/api/v1/planner/map-config")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "browser_client_id": "browser-map-id",
    }


def test_map_config_is_disabled_without_a_browser_key(tmp_path: Path) -> None:
    with make_client(tmp_path, FakeRouteProvider()) as client:
        response = client.get("/api/v1/planner/map-config")

    assert response.status_code == 200
    assert response.json() == {"enabled": False, "browser_client_id": None}


def test_route_endpoint_reports_unconfigured_provider(client: TestClient) -> None:
    response = client.post(
        "/api/v1/planner/route",
        json={"departure": "부산역", "destination": "부산인력개발원"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "route_source_not_configured"
    assert "직접 입력 거리" in response.json()["error"]["message"]


def test_route_endpoint_keeps_provider_failure_distinct_from_zero_distance(tmp_path: Path) -> None:
    with make_client(tmp_path, FailingRouteProvider()) as client:
        response = client.post(
            "/api/v1/planner/route",
            json={"departure": "부산역", "destination": "부산인력개발원"},
        )

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "route_source_unavailable",
        "message": "실제 경로를 조회할 수 없습니다. 잠시 후 다시 시도하거나 직접 입력 거리로 계산해 주세요.",
        "retryable": True,
        "details": None,
    }


def test_route_endpoint_identifies_the_unresolved_address_field(tmp_path: Path) -> None:
    with make_client(tmp_path, MissingDestinationProvider()) as client:
        response = client.post(
            "/api/v1/planner/route",
            json={"departure": "부산역", "destination": "모호한 장소"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "route_location_not_found"
    assert response.json()["error"]["details"] == [{"field": "destination"}]
