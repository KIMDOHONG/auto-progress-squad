import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ManualHub } from "./ManualHub";
import { DEFAULT_VEHICLES } from "../../lib/vehicle";

describe("manual ingestion status", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("does not imply that the public browser demo stores manufacturer PDFs", () => {
    render(<ManualHub
      vehicle={DEFAULT_VEHICLES[0]}
      syncStatus={{ mode: "local", label: "브라우저 저장", detail: "로컬" }}
    />);

    expect(screen.getByText("서버 연결 필요")).toBeInTheDocument();
    expect(screen.getByText(/공개 데모는 PDF를 저장하지 않습니다/)).toBeInTheDocument();
    expect(screen.getByText("검색: 준비 완료 전 차단")).toBeInTheDocument();
  });

  it("shows the server-side pending state and keeps search blocked", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        vehicle_id: "sample-nexo",
        status: "pending",
        document_key: "hmc:FE:2021",
        source_url: "https://ownersmanual.hyundai.com/manual/example",
        attempt_count: 0,
        failure_code: null,
        failure_message: null,
        queued_at: "2026-08-28 10:00:00",
        updated_at: "2026-08-28 10:00:00",
        ready_at: null,
        can_search: false,
      }),
    } as Response);

    render(<ManualHub
      vehicle={DEFAULT_VEHICLES[0]}
      syncStatus={{
        mode: "api",
        label: "SQLite 동기화",
        detail: "API",
        apiBaseUrl: "http://127.0.0.1:8000",
      }}
    />);

    expect(await screen.findByText("취급설명서를 확인 중입니다")).toBeInTheDocument();
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/vehicles/sample-nexo/manual-ingestion",
      expect.any(Object),
    ));
    expect(screen.getByText("검색: 준비 완료 전 차단")).toBeInTheDocument();
  });

  it("searches only after the exact vehicle manual is ready and renders sources", async () => {
    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          vehicle_id: "sample-nexo",
          status: "ready",
          document_key: "hmc:FE:2021",
          source_url: "https://ownersmanual.hyundai.com/manual/example",
          attempt_count: 0,
          failure_code: null,
          failure_message: null,
          queued_at: "2026-08-28 10:00:00",
          updated_at: "2026-08-28 10:01:00",
          ready_at: "2026-08-28 10:01:00",
          can_search: true,
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          answer: "공식 취급설명서에서 관련 내용을 찾았습니다.",
          sources: [{
            document_name: "넥쏘 2021 취급설명서",
            source_url: "https://ownersmanual.hyundai.com/manual/nexo-2021",
            page: 42,
            section: null,
            excerpt: "타이어 공기압은 운전석 도어 라벨에서 확인합니다.",
          }],
          generated_at: "2026-08-28T10:02:00+00:00",
        }),
      } as Response);

    render(<ManualHub
      vehicle={DEFAULT_VEHICLES[0]}
      syncStatus={{
        mode: "api",
        label: "SQLite 동기화",
        detail: "API",
        apiBaseUrl: "http://127.0.0.1:8000",
      }}
    />);

    expect(await screen.findByText("AI 매뉴얼 검색 준비 완료")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("설명서에서 찾을 내용"), {
      target: { value: "타이어 공기압은?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "설명서 검색" }));

    expect(await screen.findByText("공식 취급설명서에서 관련 내용을 찾았습니다.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "넥쏘 2021 취급설명서" })).toHaveAttribute(
      "href",
      "https://ownersmanual.hyundai.com/manual/nexo-2021",
    );
    expect(screen.getByText("42쪽")).toBeInTheDocument();
    await waitFor(() => expect(globalThis.fetch).toHaveBeenLastCalledWith(
      "http://127.0.0.1:8000/api/v1/manual/search",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ vehicle_id: "sample-nexo", question: "타이어 공기압은?", limit: 5 }),
      }),
    ));
  });
});
