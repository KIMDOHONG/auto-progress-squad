import { getPlannerMapConfig, lookupApiRoute, resolveApiLocation, reverseApiLocation } from "./routeApi";

describe("route API", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("maps the backend route response without exposing provider credentials", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        departure: { query: "부산역", address: "부산 동구 중앙대로 206", longitude: 129.04, latitude: 35.11 },
        destination: { query: "부산인력개발원", address: "부산 남구 용당동", longitude: 129.09, latitude: 35.12 },
        distance_km: 12.7,
        duration_minutes: 21,
        route_option: "trafast",
        toll_fare: 1200,
        fuel_price: 1800,
        path: [{ longitude: 129.04, latitude: 35.11 }, { longitude: 129.09, latitude: 35.12 }],
        alternatives: [{
          distance_km: 12.7,
          duration_minutes: 21,
          route_option: "trafast",
          toll_fare: 1200,
          fuel_price: 1800,
          path: [{ longitude: 129.04, latitude: 35.11 }, { longitude: 129.09, latitude: 35.12 }],
        }],
        source_name: "NAVER Maps",
        source_url: "https://www.ncloud.com/product/applicationService/maps",
        retrieved_at: "2026-09-01T03:00:00+00:00",
      }),
    } as Response);

    const result = await lookupApiRoute("http://127.0.0.1:8000", "부산역", "부산인력개발원");

    expect(result.distanceKm).toBe(12.7);
    expect(result.durationMinutes).toBe(21);
    expect(result.sourceName).toBe("NAVER Maps");
    expect(result.path).toHaveLength(2);
    expect(result.alternatives).toHaveLength(1);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/planner/route",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ departure: "부산역", destination: "부산인력개발원" }),
      }),
    );
  });

  it("maps exact-address, GPS reverse-address, and browser map configuration responses", async () => {
    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ location: { query: "부산역", address: "부산 동구 중앙대로 206", longitude: 129.04, latitude: 35.11 } }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ location: { query: "현재 위치", address: "부산 영도구 태종로 423", longitude: 129.06, latitude: 35.09 } }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ enabled: true, browser_client_id: "browser-id" }),
      } as Response);

    expect((await resolveApiLocation("http://127.0.0.1:8000", "부산역", "departure")).address).toContain("중앙대로");
    expect((await reverseApiLocation("http://127.0.0.1:8000", 129.06, 35.09)).query).toBe("현재 위치");
    expect(await getPlannerMapConfig("http://127.0.0.1:8000")).toEqual({ enabled: true, browserClientId: "browser-id" });
  });

  it("sends confirmed coordinates so route lookup does not geocode the GPS address again", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        departure: { query: "현재 위치", address: "확인된 출발지", longitude: 129.04, latitude: 35.11 },
        destination: { query: "청학남로 48", address: "확인된 목적지", longitude: 129.09, latitude: 35.12 },
        distance_km: 5,
        duration_minutes: 10,
        route_option: "trafast",
        toll_fare: 0,
        fuel_price: 0,
        path: [{ longitude: 129.04, latitude: 35.11 }, { longitude: 129.09, latitude: 35.12 }],
        alternatives: [],
        source_name: "NAVER Maps",
        source_url: "https://www.ncloud.com/product/applicationService/maps",
        retrieved_at: "2026-09-03T03:00:00+00:00",
      }),
    } as Response);
    const departure = { query: "현재 위치", address: "확인된 출발지", longitude: 129.04, latitude: 35.11 };
    const destination = { query: "청학남로 48", address: "확인된 목적지", longitude: 129.09, latitude: 35.12 };

    await lookupApiRoute("http://127.0.0.1:8000", departure, destination);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/planner/route",
      expect.objectContaining({
        body: JSON.stringify({
          departure: "확인된 출발지",
          destination: "확인된 목적지",
          departure_location: departure,
          destination_location: destination,
        }),
      }),
    );
  });

  it("preserves the backend failure reason for the manual fallback UI", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ error: {
        code: "route_source_not_configured",
        message: "실제 경로 조회 API가 설정되지 않았습니다. 직접 입력 거리로 계산해 주세요.",
      } }),
    } as Response);

    await expect(lookupApiRoute("http://127.0.0.1:8000", "부산역", "부산인력개발원"))
      .rejects.toEqual(expect.objectContaining({
        code: "route_source_not_configured",
        message: "실제 경로 조회 API가 설정되지 않았습니다. 직접 입력 거리로 계산해 주세요.",
      }));
  });
});
