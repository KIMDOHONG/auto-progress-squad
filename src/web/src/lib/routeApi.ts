export interface RouteLocationResult {
  query: string;
  address: string;
  longitude: number;
  latitude: number;
}

export interface RouteLookupResult {
  departure: RouteLocationResult;
  destination: RouteLocationResult;
  distanceKm: number;
  durationMinutes: number;
  routeOption: "trafast";
  sourceName: string;
  sourceUrl: string;
  retrievedAt: string;
}

interface ApiRouteLookupResult {
  departure: RouteLocationResult;
  destination: RouteLocationResult;
  distance_km: number;
  duration_minutes: number;
  route_option: "trafast";
  source_name: string;
  source_url: string;
  retrieved_at: string;
}

interface ApiErrorPayload {
  error?: { code?: string; message?: string };
}

export class RouteApiError extends Error {
  constructor(public readonly code: string, message: string) {
    super(message);
  }
}

export async function lookupApiRoute(
  baseUrl: string,
  departure: string,
  destination: string,
): Promise<RouteLookupResult> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/planner/route`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ departure, destination }),
    });
  } catch {
    throw new RouteApiError(
      "network_error",
      "경로 조회 서버에 연결할 수 없습니다. 직접 입력 거리로 계산해 주세요.",
    );
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as ApiErrorPayload;
    throw new RouteApiError(
      payload.error?.code ?? "route_api_error",
      payload.error?.message ?? "실제 경로를 조회하지 못했습니다. 직접 입력 거리로 계산해 주세요.",
    );
  }

  const payload = await response.json() as ApiRouteLookupResult;
  return {
    departure: payload.departure,
    destination: payload.destination,
    distanceKm: payload.distance_km,
    durationMinutes: payload.duration_minutes,
    routeOption: payload.route_option,
    sourceName: payload.source_name,
    sourceUrl: payload.source_url,
    retrievedAt: payload.retrieved_at,
  };
}
