import { lookupApiRoute } from "./routeApi";

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
        source_name: "NAVER Maps",
        source_url: "https://www.ncloud.com/product/applicationService/maps",
        retrieved_at: "2026-09-01T03:00:00+00:00",
      }),
    } as Response);

    const result = await lookupApiRoute("http://127.0.0.1:8000", "부산역", "부산인력개발원");

    expect(result.distanceKm).toBe(12.7);
    expect(result.durationMinutes).toBe(21);
    expect(result.sourceName).toBe("NAVER Maps");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/planner/route",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ departure: "부산역", destination: "부산인력개발원" }),
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
