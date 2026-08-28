import { attachApiManualAdapter, VehicleApiError } from "./vehicleApi";

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
