export interface RouteLocationResult {
  query: string;
  address: string;
  longitude: number;
  latitude: number;
}

export type RouteOption = "trafast" | "traoptimal" | "traavoidtoll";

export interface RouteCoordinateResult {
  longitude: number;
  latitude: number;
}

export interface RouteAlternativeResult {
  distanceKm: number;
  durationMinutes: number;
  routeOption: RouteOption;
  tollFare: number;
  fuelPrice: number;
  path: RouteCoordinateResult[];
}

export interface RouteLookupResult extends RouteAlternativeResult {
  departure: RouteLocationResult;
  destination: RouteLocationResult;
  alternatives: RouteAlternativeResult[];
  sourceName: string;
  sourceUrl: string;
  retrievedAt: string;
}

interface ApiRouteAlternativeResult {
  distance_km: number;
  duration_minutes: number;
  route_option: RouteOption;
  toll_fare: number;
  fuel_price: number;
  path: RouteCoordinateResult[];
}

interface ApiRouteLookupResult extends ApiRouteAlternativeResult {
  departure: RouteLocationResult;
  destination: RouteLocationResult;
  alternatives: ApiRouteAlternativeResult[];
  source_name: string;
  source_url: string;
  retrieved_at: string;
}

interface ApiLocationLookupResult {
  location: RouteLocationResult;
}

interface ApiMapConfigResult {
  enabled: boolean;
  browser_client_id: string | null;
}

interface ApiErrorPayload {
  error?: { code?: string; message?: string };
}

export interface PlannerMapConfig {
  enabled: boolean;
  browserClientId: string | null;
}

export class RouteApiError extends Error {
  constructor(public readonly code: string, message: string) {
    super(message);
  }
}

async function readApiResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as ApiErrorPayload;
    throw new RouteApiError(
      payload.error?.code ?? "route_api_error",
      payload.error?.message ?? fallbackMessage,
    );
  }
  return response.json() as Promise<T>;
}

async function plannerFetch<T>(
  url: string,
  init: RequestInit,
  networkMessage: string,
  fallbackMessage: string,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new RouteApiError("network_error", networkMessage);
  }
  return readApiResponse<T>(response, fallbackMessage);
}

function mapAlternative(payload: ApiRouteAlternativeResult): RouteAlternativeResult {
  return {
    distanceKm: payload.distance_km,
    durationMinutes: payload.duration_minutes,
    routeOption: payload.route_option,
    tollFare: payload.toll_fare,
    fuelPrice: payload.fuel_price,
    path: payload.path,
  };
}

export async function resolveApiLocation(
  baseUrl: string,
  query: string,
  field: "departure" | "destination",
): Promise<RouteLocationResult> {
  const payload = await plannerFetch<ApiLocationLookupResult>(
    `${baseUrl}/api/v1/planner/location/resolve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, field }),
    },
    "주소 확인 서버에 연결할 수 없습니다.",
    "주소를 확인하지 못했습니다.",
  );
  return payload.location;
}

export async function reverseApiLocation(
  baseUrl: string,
  longitude: number,
  latitude: number,
): Promise<RouteLocationResult> {
  const payload = await plannerFetch<ApiLocationLookupResult>(
    `${baseUrl}/api/v1/planner/location/reverse`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ longitude, latitude }),
    },
    "현재 위치 주소 변환 서버에 연결할 수 없습니다.",
    "현재 위치의 주소를 확인하지 못했습니다.",
  );
  return payload.location;
}

export async function getPlannerMapConfig(baseUrl: string): Promise<PlannerMapConfig> {
  const payload = await plannerFetch<ApiMapConfigResult>(
    `${baseUrl}/api/v1/planner/map-config`,
    { method: "GET" },
    "지도 설정 서버에 연결할 수 없습니다.",
    "지도 설정을 확인하지 못했습니다.",
  );
  return {
    enabled: payload.enabled,
    browserClientId: payload.browser_client_id,
  };
}

export async function lookupApiRoute(
  baseUrl: string,
  departure: string | RouteLocationResult,
  destination: string | RouteLocationResult,
): Promise<RouteLookupResult> {
  const departureLocation = typeof departure === "string" ? undefined : departure;
  const destinationLocation = typeof destination === "string" ? undefined : destination;
  const payload = await plannerFetch<ApiRouteLookupResult>(
    `${baseUrl}/api/v1/planner/route`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        departure: departureLocation?.address ?? departure,
        destination: destinationLocation?.address ?? destination,
        departure_location: departureLocation,
        destination_location: destinationLocation,
      }),
    },
    "경로 조회 서버에 연결할 수 없습니다. 직접 입력 거리로 계산해 주세요.",
    "실제 경로를 조회하지 못했습니다. 직접 입력 거리로 계산해 주세요.",
  );

  return {
    ...mapAlternative(payload),
    departure: payload.departure,
    destination: payload.destination,
    alternatives: payload.alternatives.map(mapAlternative),
    sourceName: payload.source_name,
    sourceUrl: payload.source_url,
    retrievedAt: payload.retrieved_at,
  };
}
