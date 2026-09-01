from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


JsonTransport = Callable[[str, Mapping[str, str], float], Mapping[str, Any]]


class RouteProviderError(Exception):
    """Raised when an upstream route provider cannot return a trustworthy route."""


class RouteLocationNotFoundError(RouteProviderError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(field)


@dataclass(frozen=True, slots=True)
class RouteLocation:
    query: str
    address: str
    longitude: float
    latitude: float


@dataclass(frozen=True, slots=True)
class RouteLookup:
    departure: RouteLocation
    destination: RouteLocation
    distance_meters: int
    duration_milliseconds: int
    route_option: str


class RouteProvider(Protocol):
    source_name: str
    source_url: str

    def lookup_route(self, departure: str, destination: str) -> RouteLookup: ...


def _default_json_transport(
    url: str, headers: Mapping[str, str], timeout_seconds: float
) -> Mapping[str, Any]:
    request = Request(url, headers=dict(headers), method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        raise RouteProviderError("NAVER Maps 요청에 실패했습니다.") from error
    if not isinstance(payload, Mapping):
        raise RouteProviderError("NAVER Maps 응답 형식이 올바르지 않습니다.")
    return payload


class NaverMapsRouteProvider:
    source_name = "NAVER Maps"
    source_url = "https://www.ncloud.com/product/applicationService/maps"
    _geocode_endpoint = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
    _directions_endpoint = "https://maps.apigw.ntruss.com/map-direction/v1/driving"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        timeout_seconds: float = 5.0,
        transport: JsonTransport | None = None,
    ) -> None:
        if not client_id.strip() or not client_secret.strip():
            raise ValueError("NAVER Maps client ID and secret are required")
        if timeout_seconds <= 0:
            raise ValueError("NAVER Maps timeout must be greater than zero")
        self._headers = {
            "Accept": "application/json",
            "x-ncp-apigw-api-key-id": client_id,
            "x-ncp-apigw-api-key": client_secret,
        }
        self._timeout_seconds = timeout_seconds
        self._transport = transport or _default_json_transport

    def _request(self, endpoint: str, params: Mapping[str, str]) -> Mapping[str, Any]:
        return self._transport(
            f"{endpoint}?{urlencode(params)}",
            self._headers,
            self._timeout_seconds,
        )

    def _geocode(self, query: str, field: str) -> RouteLocation:
        payload = self._request(
            self._geocode_endpoint,
            {"query": query, "count": "1", "language": "kor"},
        )
        addresses = payload.get("addresses")
        if not isinstance(addresses, list) or not addresses:
            raise RouteLocationNotFoundError(field)
        address = addresses[0]
        if not isinstance(address, Mapping):
            raise RouteProviderError("NAVER Maps 주소 응답 형식이 올바르지 않습니다.")
        try:
            longitude = float(address["x"])
            latitude = float(address["y"])
        except (KeyError, TypeError, ValueError) as error:
            raise RouteProviderError("NAVER Maps 주소 좌표를 확인할 수 없습니다.") from error
        if (
            not math.isfinite(longitude)
            or not math.isfinite(latitude)
            or not -180 <= longitude <= 180
            or not -90 <= latitude <= 90
        ):
            raise RouteProviderError("NAVER Maps 주소 좌표가 유효 범위를 벗어났습니다.")
        resolved_address = next(
            (
                str(address.get(key, "")).strip()
                for key in ("roadAddress", "jibunAddress", "englishAddress")
                if str(address.get(key, "")).strip()
            ),
            query,
        )
        return RouteLocation(
            query=query,
            address=resolved_address,
            longitude=longitude,
            latitude=latitude,
        )

    def lookup_route(self, departure: str, destination: str) -> RouteLookup:
        resolved_departure = self._geocode(departure, "departure")
        resolved_destination = self._geocode(destination, "destination")
        payload = self._request(
            self._directions_endpoint,
            {
                "start": f"{resolved_departure.longitude},{resolved_departure.latitude}",
                "goal": f"{resolved_destination.longitude},{resolved_destination.latitude}",
                "option": "trafast",
                "cartype": "1",
                "lang": "ko",
            },
        )
        route = payload.get("route")
        candidates = route.get("trafast") if isinstance(route, Mapping) else None
        if not isinstance(candidates, list) or not candidates:
            raise RouteProviderError("NAVER Maps에서 주행 경로를 찾지 못했습니다.")
        first_route = candidates[0]
        summary = first_route.get("summary") if isinstance(first_route, Mapping) else None
        if not isinstance(summary, Mapping):
            raise RouteProviderError("NAVER Maps 경로 응답 형식이 올바르지 않습니다.")
        try:
            distance_meters = int(summary["distance"])
            duration_milliseconds = int(summary["duration"])
        except (KeyError, TypeError, ValueError) as error:
            raise RouteProviderError("NAVER Maps 경로 요약을 확인할 수 없습니다.") from error
        if distance_meters <= 0 or duration_milliseconds < 0:
            raise RouteProviderError("NAVER Maps 경로 값이 올바르지 않습니다.")
        return RouteLookup(
            departure=resolved_departure,
            destination=resolved_destination,
            distance_meters=distance_meters,
            duration_milliseconds=duration_milliseconds,
            route_option="trafast",
        )
