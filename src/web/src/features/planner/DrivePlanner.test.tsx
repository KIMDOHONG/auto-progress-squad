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

function response(payload: object, ok = true, status = 200): Response {
  return { ok, status, json: async () => payload } as Response;
}

function locationPayload(query: string, address: string, longitude: number, latitude: number) {
  return { location: { query, address, longitude, latitude } };
}

const routePayload = {
  departure: { query: "부산 동구 중앙대로 206", address: "부산 동구 중앙대로 206", longitude: 129.04, latitude: 35.11 },
  destination: { query: "부산 남구 용당동 546-2", address: "부산 남구 용당동 546-2", longitude: 129.09, latitude: 35.12 },
  distance_km: 12.7,
  duration_minutes: 21,
  route_option: "trafast",
  toll_fare: 1200,
  fuel_price: 1800,
  path: [{ longitude: 129.04, latitude: 35.11 }, { longitude: 129.09, latitude: 35.12 }],
  alternatives: [
    {
      distance_km: 12.7,
      duration_minutes: 21,
      route_option: "trafast",
      toll_fare: 1200,
      fuel_price: 1800,
      path: [{ longitude: 129.04, latitude: 35.11 }, { longitude: 129.09, latitude: 35.12 }],
    },
    {
      distance_km: 14.2,
      duration_minutes: 24,
      route_option: "traavoidtoll",
      toll_fare: 0,
      fuel_price: 1900,
      path: [{ longitude: 129.04, latitude: 35.11 }, { longitude: 129.07, latitude: 35.13 }, { longitude: 129.09, latitude: 35.12 }],
    },
  ],
  source_name: "NAVER Maps",
  source_url: "https://www.ncloud.com/product/applicationService/maps",
  retrieved_at: "2026-09-01T03:00:00+00:00",
};

async function confirmBothAddresses() {
  fireEvent.change(screen.getByLabelText("출발지 정확한 주소"), { target: { value: "부산역" } });
  fireEvent.click(screen.getByRole("button", { name: "출발지 주소 확인" }));
  expect(await screen.findByText(/확인됨 · 부산 동구 중앙대로 206/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("목적지 정확한 주소"), { target: { value: "부산인력개발원" } });
  fireEvent.click(screen.getByRole("button", { name: "목적지 주소 확인" }));
  expect(await screen.findByText(/확인됨 · 부산 남구 용당동 546-2/)).toBeInTheDocument();
}

describe("DrivePlanner route lookup", () => {
  const originalFetch = globalThis.fetch;
  const originalGeolocation = navigator.geolocation;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    Object.defineProperty(navigator, "geolocation", { configurable: true, value: originalGeolocation });
    vi.restoreAllMocks();
  });

  it("confirms exact addresses, renders route geometry, and recalculates the selected route", async () => {
    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce(response(locationPayload("부산역", "부산 동구 중앙대로 206", 129.04, 35.11)))
      .mockResolvedValueOnce(response(locationPayload("부산인력개발원", "부산 남구 용당동 546-2", 129.09, 35.12)))
      .mockResolvedValueOnce(response(routePayload))
      .mockResolvedValueOnce(response({ enabled: false, browser_client_id: null }));
    render(<DrivePlanner vehicle={vehicle} apiBaseUrl="http://127.0.0.1:8000" />);
    await confirmBothAddresses();

    fireEvent.click(screen.getByRole("button", { name: "실제 경로 조회 후 계산" }));

    expect(await screen.findByText("12.7 km · 약 21분 · 통행료 1,200원")).toBeInTheDocument();
    expect(screen.getByLabelText("실제 경로 좌표 미리보기")).toBeInTheDocument();
    expect(screen.getByLabelText(/경로 거리/)).toHaveValue(12.7);
    fireEvent.click(screen.getByRole("button", { name: /무료 우선/ }));
    expect(screen.getByLabelText(/경로 거리/)).toHaveValue(14.2);
    const result = within(screen.getByLabelText("로컬 플래너 계산 결과"));
    expect(result.getByText("계산 완료")).toBeInTheDocument();
    expect(result.getByText("API 거리 + 로컬 계산")).toBeInTheDocument();
    expect(result.getByText(/경로 거리는 NAVER Maps 조회 결과를 사용했습니다/)).toBeInTheDocument();
  });

  it("keeps the direct distance calculation available when route lookup is unavailable", async () => {
    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce(response(locationPayload("부산역", "부산 동구 중앙대로 206", 129.04, 35.11)))
      .mockResolvedValueOnce(response(locationPayload("부산인력개발원", "부산 남구 용당동 546-2", 129.09, 35.12)))
      .mockResolvedValueOnce(response({ error: {
        code: "route_source_not_configured",
        message: "실제 경로 조회 API가 설정되지 않았습니다. 직접 입력 거리로 계산해 주세요.",
      } }, false, 503))
      .mockResolvedValueOnce(response({ enabled: false, browser_client_id: null }));
    render(<DrivePlanner vehicle={vehicle} apiBaseUrl="http://127.0.0.1:8000" />);
    await confirmBothAddresses();

    fireEvent.click(screen.getByRole("button", { name: "실제 경로 조회 후 계산" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("실제 경로 조회 API가 설정되지 않았습니다");

    fireEvent.change(screen.getByLabelText(/경로 거리/), { target: { value: "100" } });
    fireEvent.click(screen.getByRole("button", { name: "직접 입력 거리로 계산" }));
    expect(within(screen.getByLabelText("로컬 플래너 계산 결과")).getByText("계산 완료")).toBeInTheDocument();
  });

  it("uses browser GPS and the server reverse-geocoded address for departure", async () => {
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: {
        getCurrentPosition: (success: PositionCallback) => success({
          coords: { longitude: 129.0689, latitude: 35.0912 },
        } as GeolocationPosition),
      },
    });
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      response(locationPayload("현재 위치", "부산 영도구 태종로 423", 129.0689, 35.0912)),
    );
    render(<DrivePlanner vehicle={vehicle} apiBaseUrl="http://127.0.0.1:8000" />);

    fireEvent.click(screen.getByRole("button", { name: "GPS 현재 위치" }));

    expect(await screen.findByDisplayValue("부산 영도구 태종로 423")).toBeInTheDocument();
    expect(screen.getByText(/확인됨 · 부산 영도구 태종로 423/)).toBeInTheDocument();
  });
});
