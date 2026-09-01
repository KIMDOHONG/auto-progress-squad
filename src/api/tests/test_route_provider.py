from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.route_provider import (
    NaverMapsRouteProvider,
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
        return {"route": {"trafast": [{"summary": {"distance": 12654, "duration": 1_234_567}}]}}

    provider = NaverMapsRouteProvider(
        "client-id", "client-secret", timeout_seconds=3.5, transport=transport
    )
    result = provider.lookup_route("부산역", "부산인력개발원")

    assert result.distance_meters == 12654
    assert result.duration_milliseconds == 1_234_567
    assert result.route_option == "trafast"
    assert result.departure.address == "부산 동구 중앙대로 206"
    assert result.destination.address == "부산 남구 용당동 546-2"
    assert len(calls) == 3
    assert parse_qs(urlparse(calls[2][0]).query) == {
        "start": ["129.0403,35.1151"],
        "goal": ["129.0964,35.1266"],
        "option": ["trafast"],
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


class FakeRouteProvider:
    source_name = "검증 경로 공급자"
    source_url = "https://example.com/routes"

    def lookup_route(self, departure: str, destination: str) -> RouteLookup:
        return RouteLookup(
            departure=RouteLocation(departure, "부산 동구 중앙대로 206", 129.0403, 35.1151),
            destination=RouteLocation(destination, "부산 남구 용당동 546-2", 129.0964, 35.1266),
            distance_meters=12_654,
            duration_milliseconds=1_234_567,
            route_option="trafast",
        )


class FailingRouteProvider(FakeRouteProvider):
    def lookup_route(self, departure: str, destination: str) -> RouteLookup:
        raise RouteProviderError("upstream failed")


class MissingDestinationProvider(FakeRouteProvider):
    def lookup_route(self, departure: str, destination: str) -> RouteLookup:
        raise RouteLocationNotFoundError("destination")


def make_client(tmp_path: Path, provider: object) -> TestClient:
    settings = Settings(
        database_path=tmp_path / "route-test.db",
        cors_origins=("http://127.0.0.1:5173",),
        manual_source_dir=tmp_path / "manuals",
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
    assert payload["source_name"] == "검증 경로 공급자"
    assert payload["departure"]["query"] == "부산역"
    assert payload["destination"]["address"] == "부산 남구 용당동 546-2"
    assert payload["retrieved_at"]


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
