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
class RouteCoordinate:
    longitude: float
    latitude: float


@dataclass(frozen=True, slots=True)
class RouteAlternative:
    route_option: str
    distance_meters: int
    duration_milliseconds: int
    toll_fare: int
    fuel_price: int
    path: tuple[RouteCoordinate, ...]


@dataclass(frozen=True, slots=True)
class RouteLookup:
    departure: RouteLocation
    destination: RouteLocation
    distance_meters: int
    duration_milliseconds: int
    route_option: str
    toll_fare: int = 0
    fuel_price: int = 0
    path: tuple[RouteCoordinate, ...] = ()
    alternatives: tuple[RouteAlternative, ...] = ()


class RouteProvider(Protocol):
    source_name: str
    source_url: str

    def resolve_location(self, query: str, field: str = "location") -> RouteLocation: ...

    def reverse_location(self, longitude: float, latitude: float) -> RouteLocation: ...

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
    _reverse_geocode_endpoint = "https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc"
    _directions_endpoint = "https://maps.apigw.ntruss.com/map-direction/v1/driving"
    _route_options = ("trafast", "traoptimal", "traavoidtoll")

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

    @staticmethod
    def _validate_coordinates(longitude: float, latitude: float) -> None:
        if (
            not math.isfinite(longitude)
            or not math.isfinite(latitude)
            or not -180 <= longitude <= 180
            or not -90 <= latitude <= 90
        ):
            raise RouteProviderError("NAVER Maps 주소 좌표가 유효 범위를 벗어났습니다.")

    def resolve_location(self, query: str, field: str = "location") -> RouteLocation:
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
        self._validate_coordinates(longitude, latitude)
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

    @staticmethod
    def _reverse_address(result: Mapping[str, Any]) -> str:
        region = result.get("region")
        land = result.get("land")
        if not isinstance(region, Mapping):
            return ""
        parts = []
        for index in range(1, 5):
            area = region.get(f"area{index}")
            if isinstance(area, Mapping):
                name = str(area.get("name", "")).strip()
                if name:
                    parts.append(name)
        if isinstance(land, Mapping):
            road_name = str(land.get("name", "")).strip()
            number1 = str(land.get("number1", "")).strip()
            number2 = str(land.get("number2", "")).strip()
            if road_name:
                parts.append(road_name)
            if number1:
                parts.append(f"{number1}-{number2}" if number2 else number1)
            addition = land.get("addition0")
            if isinstance(addition, Mapping):
                building = str(addition.get("value", "")).strip()
                if building:
                    parts.append(building)
        return " ".join(parts)

    def reverse_location(self, longitude: float, latitude: float) -> RouteLocation:
        self._validate_coordinates(longitude, latitude)
        payload = self._request(
            self._reverse_geocode_endpoint,
            {
                "coords": f"{longitude},{latitude}",
                "sourcecrs": "EPSG:4326",
                "orders": "roadaddr,addr,admcode,legalcode",
                "output": "json",
            },
        )
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            raise RouteLocationNotFoundError("departure")
        address = ""
        for result in results:
            if not isinstance(result, Mapping):
                continue
            address = self._reverse_address(result)
            if address:
                break
        if not address:
            raise RouteProviderError("NAVER Maps 역주소 응답 형식이 올바르지 않습니다.")
        return RouteLocation(
            query="현재 위치",
            address=address,
            longitude=longitude,
            latitude=latitude,
        )

    @classmethod
    def _parse_alternative(
        cls, route_option: str, candidate: Mapping[str, Any]
    ) -> RouteAlternative:
        summary = candidate.get("summary")
        path_payload = candidate.get("path")
        if not isinstance(summary, Mapping) or not isinstance(path_payload, list):
            raise RouteProviderError("NAVER Maps 경로 응답 형식이 올바르지 않습니다.")
        try:
            distance_meters = int(summary["distance"])
            duration_milliseconds = int(summary["duration"])
            toll_fare = int(summary.get("tollFare", 0))
            fuel_price = int(summary.get("fuelPrice", 0))
        except (KeyError, TypeError, ValueError) as error:
            raise RouteProviderError("NAVER Maps 경로 요약을 확인할 수 없습니다.") from error
        if distance_meters <= 0 or duration_milliseconds < 0:
            raise RouteProviderError("NAVER Maps 경로 값이 올바르지 않습니다.")

        path: list[RouteCoordinate] = []
        for point in path_payload:
            if not isinstance(point, list) or len(point) < 2:
                raise RouteProviderError("NAVER Maps 경로 좌표 형식이 올바르지 않습니다.")
            try:
                longitude = float(point[0])
                latitude = float(point[1])
            except (TypeError, ValueError) as error:
                raise RouteProviderError("NAVER Maps 경로 좌표를 확인할 수 없습니다.") from error
            cls._validate_coordinates(longitude, latitude)
            path.append(RouteCoordinate(longitude, latitude))
        if len(path) < 2:
            raise RouteProviderError("NAVER Maps 경로 좌표가 충분하지 않습니다.")
        return RouteAlternative(
            route_option=route_option,
            distance_meters=distance_meters,
            duration_milliseconds=duration_milliseconds,
            toll_fare=max(0, toll_fare),
            fuel_price=max(0, fuel_price),
            path=tuple(path),
        )

    def lookup_route(self, departure: str, destination: str) -> RouteLookup:
        resolved_departure = self.resolve_location(departure, "departure")
        resolved_destination = self.resolve_location(destination, "destination")
        payload = self._request(
            self._directions_endpoint,
            {
                "start": f"{resolved_departure.longitude},{resolved_departure.latitude}",
                "goal": f"{resolved_destination.longitude},{resolved_destination.latitude}",
                "option": ":".join(self._route_options),
                "cartype": "1",
                "lang": "ko",
            },
        )
        route = payload.get("route")
        if not isinstance(route, Mapping):
            raise RouteProviderError("NAVER Maps에서 주행 경로를 찾지 못했습니다.")
        alternatives: list[RouteAlternative] = []
        for route_option in self._route_options:
            candidates = route.get(route_option)
            if not isinstance(candidates, list) or not candidates:
                continue
            candidate = candidates[0]
            if not isinstance(candidate, Mapping):
                raise RouteProviderError("NAVER Maps 경로 응답 형식이 올바르지 않습니다.")
            alternatives.append(self._parse_alternative(route_option, candidate))
        if not alternatives:
            raise RouteProviderError("NAVER Maps에서 주행 경로를 찾지 못했습니다.")
        primary = alternatives[0]
        return RouteLookup(
            departure=resolved_departure,
            destination=resolved_destination,
            distance_meters=primary.distance_meters,
            duration_milliseconds=primary.duration_milliseconds,
            route_option=primary.route_option,
            toll_fare=primary.toll_fare,
            fuel_price=primary.fuel_price,
            path=primary.path,
            alternatives=tuple(alternatives),
        )
