import { fireEvent, render, screen, within } from "@testing-library/react";
import type { VehicleProfile } from "../../types";
import { DrivePlanner } from "./DrivePlanner";

const vehicle: VehicleProfile = {
  id: "test-ev",
  nickname: "테스트 EV",
  manufacturer: "제네시스",
  model: "ELECTRIFIED GV70",
  modelYear: 2027,
  powertrain: "electric",
  batteryCapacityKwh: 84,
};

describe("DrivePlanner route lookup", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("uses a successful route distance and then runs the local energy calculation", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        departure: { query: "부산역", address: "부산 동구 중앙대로 206", longitude: 129.04, latitude: 35.11 },
        destination: { query: "부산인력개발원", address: "부산 남구 용당동 546-2", longitude: 129.09, latitude: 35.12 },
        distance_km: 12.7,
        duration_minutes: 21,
        route_option: "trafast",
        source_name: "NAVER Maps",
        source_url: "https://www.ncloud.com/product/applicationService/maps",
        retrieved_at: "2026-09-01T03:00:00+00:00",
      }),
    } as Response);
    render(<DrivePlanner vehicle={vehicle} apiBaseUrl="http://127.0.0.1:8000" />);
    fireEvent.change(screen.getByLabelText("출발지 주소"), { target: { value: "부산역" } });
    fireEvent.change(screen.getByLabelText("목적지 주소"), { target: { value: "부산인력개발원" } });

    fireEvent.click(screen.getByRole("button", { name: "실제 경로 조회 후 계산" }));

    expect(await screen.findByText("12.7 km · 약 21분")).toBeInTheDocument();
    expect(screen.getByLabelText(/경로 거리/)).toHaveValue(12.7);
    const result = within(screen.getByLabelText("로컬 플래너 계산 결과"));
    expect(result.getByText("계산 완료")).toBeInTheDocument();
    expect(result.getByText("API 거리 + 로컬 계산")).toBeInTheDocument();
    expect(result.getByText(/경로 거리는 NAVER Maps 조회 결과를 사용했습니다/)).toBeInTheDocument();
  });

  it("keeps the direct distance calculation available when route lookup is unavailable", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ error: {
        code: "route_source_not_configured",
        message: "실제 경로 조회 API가 설정되지 않았습니다. 직접 입력 거리로 계산해 주세요.",
      } }),
    } as Response);
    render(<DrivePlanner vehicle={vehicle} apiBaseUrl="http://127.0.0.1:8000" />);

    fireEvent.click(screen.getByRole("button", { name: "실제 경로 조회 후 계산" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("실제 경로 조회 API가 설정되지 않았습니다");

    fireEvent.change(screen.getByLabelText(/경로 거리/), { target: { value: "100" } });
    fireEvent.click(screen.getByRole("button", { name: "직접 입력 거리로 계산" }));
    expect(within(screen.getByLabelText("로컬 플래너 계산 결과")).getByText("계산 완료")).toBeInTheDocument();
  });
});
