import { attachApiManualAdapter, getApiRecalls, VehicleApiError } from "./vehicleApi";

describe("vehicle API manual adapter errors", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("preserves safe generation choices from a 409 response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({
        error: {
          code: "manual_generation_required",
          message: "세대를 선택해 주세요.",
          retryable: false,
          details: [
            {
              generation: "T1",
              manual_title: "테스트 SUV T1 취급설명서",
              source_checked_at: "2026-08-28",
            },
          ],
        },
      }),
    } as Response);

    const request = attachApiManualAdapter(
      "http://127.0.0.1:8000",
      "kgm-test",
      "kgm",
    );

    await expect(request).rejects.toEqual(expect.objectContaining({
      code: "manual_generation_required",
      details: [{
        generation: "T1",
        manual_title: "테스트 SUV T1 취급설명서",
        source_checked_at: "2026-08-28",
      }],
    } satisfies Partial<VehicleApiError>));
  });
});

describe("vehicle API recall lookup", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("maps the official query scope, retrieval time, and record links", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        vehicle_id: "stinger/2021",
        status: "matched",
        query: {
          manufacturer: "기아",
          model: "스팅어",
          model_year: 2021,
          generation: "CK",
          project_code: "SC",
          lookup_key: "기아|스팅어|2021|CK|SC",
        },
        items: [{
          recall_id: "KOR-2026-001",
          title: "평가용 리콜 제목",
          published_at: "2026-08-31",
          source_url: "https://www.car.go.kr/ri/recall/detail.do?id=KOR-2026-001",
        }],
        source_name: "자동차리콜센터",
        source_url: "https://www.car.go.kr/home/main.do",
        retrieved_at: "2026-09-01T01:00:00+00:00",
      }),
    } as Response);

    await expect(getApiRecalls("http://127.0.0.1:8000", "stinger/2021")).resolves.toEqual({
      vehicleId: "stinger/2021",
      status: "matched",
      query: {
        manufacturer: "기아",
        model: "스팅어",
        modelYear: 2021,
        generation: "CK",
        projectCode: "SC",
        lookupKey: "기아|스팅어|2021|CK|SC",
      },
      items: [{
        recallId: "KOR-2026-001",
        title: "평가용 리콜 제목",
        publishedAt: "2026-08-31",
        sourceUrl: "https://www.car.go.kr/ri/recall/detail.do?id=KOR-2026-001",
      }],
      sourceName: "자동차리콜센터",
      sourceUrl: "https://www.car.go.kr/home/main.do",
      retrievedAt: "2026-09-01T01:00:00+00:00",
    });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/vehicles/stinger%2F2021/recalls",
      expect.any(Object),
    );
  });
});
