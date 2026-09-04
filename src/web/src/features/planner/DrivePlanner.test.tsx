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

  it("shows ranked charging candidates for the selected real route", async () => {
    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce(response(locationPayload("부산역", "부산 동구 중앙대로 206", 129.04, 35.11)))
      .mockResolvedValueOnce(response(locationPayload("부산인력개발원", "부산 남구 용당동 546-2", 129.09, 35.12)))
      .mockResolvedValueOnce(response(routePayload))
      .mockResolvedValueOnce(response({ enabled: false, browser_client_id: null }))
      .mockResolvedValueOnce(response({
        status: "matched",
        energy_kind: "electric",
        corridor_km: 5,
        stations: [{
          station_id: "ev-1",
          name: "영도 급속충전소",
          address: "부산 영도구 태종로 1",
          longitude: 129.05,
          latitude: 35.1,
          energy_kind: "electric",
          status: "available",
          status_observed_at: "2026-09-04T02:00:00+00:00",
          power_kw: 200,
          pressure_bar: null,
          queue_vehicle_count: null,
          trailer_pressure_bar: null,
          fuel_grades: [],
          fuel_grade_match: "not-applicable",
          distance_to_route_km: 0.4,
          route_progress_percent: 37.5,
          source_url: "https://example.com/ev-1",
        }],
        warnings: ["표시된 상태에는 충전 대기시간이 포함되지 않습니다."],
        source_name: "공식 충전소 스냅샷",
        source_url: "https://example.com/stations",
        retrieved_at: "2026-09-04T02:00:00+00:00",
      }));
    render(<DrivePlanner vehicle={vehicle} apiBaseUrl="http://127.0.0.1:8000" />);
    await confirmBothAddresses();
    fireEvent.click(screen.getByRole("button", { name: "실제 경로 조회 후 계산" }));
    expect(await screen.findByText("12.7 km · 약 21분 · 통행료 1,200원")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "경로 주변 충전소 찾기" }));

    expect(await screen.findByText("영도 급속충전소")).toBeInTheDocument();
    const candidates = within(screen.getByLabelText("선택 경로 주변 충전·주유소 후보"));
    expect(candidates.getByText("경로선에서 직선 약 0.4 km")).toBeInTheDocument();
    expect(candidates.getByText("전체 경로의 약 37.5% 지점")).toBeInTheDocument();
    expect(candidates.getByText("최대 200 kW")).toBeInTheDocument();
    expect(candidates.getByText("이용 가능")).toBeInTheDocument();
    expect(within(screen.getByLabelText("로컬 플래너 계산 결과")).getByText("외부 데이터 일부 연동")).toBeInTheDocument();
  });

  it("separates an unconfigured station provider from route and calculation results", async () => {
    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce(response(locationPayload("부산역", "부산 동구 중앙대로 206", 129.04, 35.11)))
      .mockResolvedValueOnce(response(locationPayload("부산인력개발원", "부산 남구 용당동 546-2", 129.09, 35.12)))
      .mockResolvedValueOnce(response(routePayload))
      .mockResolvedValueOnce(response({ enabled: false, browser_client_id: null }))
      .mockResolvedValueOnce(response({ error: {
        code: "station_source_not_configured",
        message: "충전·주유소 데이터 공급자가 설정되지 않았습니다.",
      } }, false, 503));
    render(<DrivePlanner vehicle={vehicle} apiBaseUrl="http://127.0.0.1:8000" />);
    await confirmBothAddresses();
    fireEvent.click(screen.getByRole("button", { name: "실제 경로 조회 후 계산" }));
    expect(await screen.findByText("12.7 km · 약 21분 · 통행료 1,200원")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "경로 주변 충전소 찾기" }));

    expect(await screen.findByText("충전·주유소 공급자 미설정")).toBeInTheDocument();
    expect(screen.getByText(/기존 주행 계산과 경로 결과는 그대로 유지됩니다/)).toBeInTheDocument();
    expect(within(screen.getByLabelText("로컬 플래너 계산 결과")).getByText("계산 완료")).toBeInTheDocument();
    expect(screen.getByText("NAVER Maps · 실시간 빠른 길")).toBeInTheDocument();
  });

  it("looks up both directions and sums a round trip", async () => {
    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce(response(locationPayload("부산역", "부산 동구 중앙대로 206", 129.04, 35.11)))
      .mockResolvedValueOnce(response(locationPayload("부산인력개발원", "부산 남구 용당동 546-2", 129.09, 35.12)))
      .mockResolvedValueOnce(response(routePayload))
      .mockResolvedValueOnce(response({
        ...routePayload,
        departure: routePayload.destination,
        destination: routePayload.departure,
      }))
      .mockResolvedValueOnce(response({ enabled: false, browser_client_id: null }));
    render(<DrivePlanner vehicle={vehicle} apiBaseUrl="http://127.0.0.1:8000" />);
    fireEvent.click(screen.getByRole("radio", { name: "왕복" }));
    await confirmBothAddresses();

    fireEvent.click(screen.getByRole("button", { name: "실제 경로 조회 후 계산" }));

    expect(await screen.findByText("NAVER Maps · 왕복 · 실시간 빠른 길")).toBeInTheDocument();
    expect(screen.getByText("25.4 km · 약 42분 · 통행료 2,400원")).toBeInTheDocument();
    expect(screen.getByLabelText(/왕복 총 경로 거리/)).toHaveValue(25.4);
    const routeCalls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls
      .filter(([url]) => String(url).endsWith("/api/v1/planner/route"));
    expect(routeCalls).toHaveLength(2);
    expect(JSON.parse(String(routeCalls[1][1]?.body))).toEqual(expect.objectContaining({
      departure: "부산 남구 용당동 546-2",
      destination: "부산 동구 중앙대로 206",
      departure_location: expect.objectContaining({ longitude: 129.09, latitude: 35.12 }),
      destination_location: expect.objectContaining({ longitude: 129.04, latitude: 35.11 }),
    }));
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
    const getCurrentPosition = vi.fn((success: PositionCallback) => success({
      coords: { longitude: 129.0689, latitude: 35.0912 },
    } as GeolocationPosition));
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: { getCurrentPosition },
    });
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      response(locationPayload("현재 위치", "부산 영도구 태종로 423", 129.0689, 35.0912)),
    );
    render(<DrivePlanner vehicle={vehicle} apiBaseUrl="http://127.0.0.1:8000" />);

    fireEvent.click(screen.getByRole("button", { name: "GPS 현재 위치" }));

    expect(await screen.findByDisplayValue("부산 영도구 태종로 423")).toBeInTheDocument();
    expect(screen.getByText(/확인됨 · 부산 영도구 태종로 423/)).toBeInTheDocument();
    expect(getCurrentPosition).toHaveBeenCalledWith(
      expect.any(Function),
      expect.any(Function),
      { enableHighAccuracy: false, timeout: 20_000, maximumAge: 300_000 },
    );
  });

  it("keeps the GPS coordinates visible when reverse geocoding is not configured", async () => {
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: {
        getCurrentPosition: (success: PositionCallback) => success({
          coords: { longitude: 129.0393984, latitude: 35.1130792 },
        } as GeolocationPosition),
      },
    });
    globalThis.fetch = vi.fn().mockResolvedValueOnce(response({ error: {
      code: "route_source_not_configured",
      message: "현재 위치 주소 변환 API가 설정되지 않았습니다. 주소를 직접 입력해 주세요.",
    } }, false, 503));
    render(<DrivePlanner vehicle={vehicle} apiBaseUrl="http://127.0.0.1:8000" />);

    fireEvent.click(screen.getByRole("button", { name: "GPS 현재 위치" }));

    expect(await screen.findByDisplayValue("GPS 35.113079, 129.039398")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("GPS 좌표는 확인했지만 주소로 변환하지 못했습니다");
    expect(screen.getByRole("alert")).toHaveTextContent("현재 위치 주소 변환 API가 설정되지 않았습니다");
  });

  it("explains when the current browser cannot provide a location", async () => {
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: {
        getCurrentPosition: (_success: PositionCallback, failure: PositionErrorCallback) => failure({
          code: 2,
          message: "position unavailable",
        } as GeolocationPositionError),
      },
    });
    render(<DrivePlanner vehicle={vehicle} apiBaseUrl="http://127.0.0.1:8000" />);

    fireEvent.click(screen.getByRole("button", { name: "GPS 현재 위치" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("현재 앱을 연 브라우저에서 위치 정보를 사용할 수 없습니다");
    expect(screen.getByRole("alert")).toHaveTextContent("Windows 위치 서비스와 이 브라우저의 위치 권한");
  });

  it("uses a stored tank capacity to calculate the required fuel and cost", () => {
    const fuelVehicle: VehicleProfile = {
      id: "test-k5",
      nickname: "K5 테스트",
      manufacturer: "기아",
      model: "K5",
      modelYear: 2026,
      powertrain: "gasoline",
      powertrainDetail: "스마트스트림 G1.6 T-GDI",
      trim: "노블레스",
      fuelGrade: "regular",
      fuelTankCapacityLiters: 60,
    };
    render(<DrivePlanner vehicle={fuelVehicle} />);

    expect(screen.getByLabelText(/연료탱크 용량/)).toHaveValue(60);
    expect(screen.getByLabelText(/연료탱크 용량/)).toHaveAttribute("readonly");
    fireEvent.change(screen.getByLabelText(/경로 거리/), { target: { value: "120" } });
    fireEvent.change(screen.getByLabelText(/현재 연료량/), { target: { value: "10" } });
    fireEvent.change(screen.getByLabelText(/최근 평균 연비/), { target: { value: "12" } });
    fireEvent.change(screen.getByLabelText(/도착 희망 잔량/), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText(/예상 연료 단가/), { target: { value: "1700" } });
    fireEvent.click(screen.getByRole("button", { name: "직접 입력 거리로 계산" }));

    const result = within(screen.getByLabelText("로컬 플래너 계산 결과"));
    expect(result.getByText("계산 완료")).toBeInTheDocument();
    expect(result.getByText("출발 전에 최소 5L를 주유해야 합니다.")).toBeInTheDocument();
    expect(result.getByText("8,500 원")).toBeInTheDocument();
    expect(result.getByText(/탱크 용량 60 L/)).toBeInTheDocument();
  });

  it("offers EV minimum or full charging and applies the selected plan", () => {
    render(<DrivePlanner vehicle={vehicle} />);

    expect(screen.getByRole("radio", { name: "필요한 만큼 충전" })).toBeChecked();
    const fullCharge = screen.getByRole("radio", { name: "출발 전 100% 충전" });
    expect(fullCharge).toBeEnabled();
    fireEvent.click(fullCharge);
    fireEvent.click(screen.getByRole("button", { name: "직접 입력 거리로 계산" }));

    const result = within(screen.getByLabelText("로컬 플래너 계산 결과"));
    expect(result.getByText("선택 충전")).toBeInTheDocument();
    expect(result.getByText("필수 충전은 아니지만 출발 전 100% 충전하는 선택으로 계산했습니다.")).toBeInTheDocument();
    expect(result.getByText(/계획 충전량 48.7 kWh · 출발 전 100% 충전 기준/)).toBeInTheDocument();
    expect(result.getByText("76.7%")).toBeInTheDocument();
  });

  it("shows current-SoC en-route energy for minimum charging and updates when the mode changes", () => {
    render(<DrivePlanner vehicle={vehicle} />);

    fireEvent.change(screen.getByLabelText(/경로 거리/), { target: { value: "455" } });
    fireEvent.click(screen.getByRole("button", { name: "직접 입력 거리로 계산" }));

    const result = within(screen.getByLabelText("로컬 플래너 계산 결과"));
    expect(result.getByText("현재 배터리 42%로 출발하면 경로 중 최소 62.3 kWh를 추가 충전해야 합니다.")).toBeInTheDocument();
    expect(result.getByText(/출발 전 충전량/).parentElement).toHaveTextContent("0 kWh");
    expect(result.getByText(/경로 중 추가량/).parentElement).toHaveTextContent("62.3 kWh");

    fireEvent.click(screen.getByRole("radio", { name: "출발 전 100% 충전" }));
    expect(result.getByText("출발 전 100% 충전해도 부족하므로 경로 중 최소 13.6 kWh를 추가 충전해야 합니다.")).toBeInTheDocument();
    expect(result.getByText(/출발 전 충전량/).parentElement).toHaveTextContent("48.7 kWh");
    expect(result.getByText(/경로 중 추가량/).parentElement).toHaveTextContent("13.6 kWh");
  });

  it("fixes hydrogen to the full-fill principle instead of offering a selectable amount", () => {
    const hydrogenVehicle: VehicleProfile = {
      id: "test-hydrogen",
      nickname: "넥쏘 테스트",
      manufacturer: "현대",
      model: "넥쏘",
      modelYear: 2021,
      powertrain: "hydrogen",
    };
    render(<DrivePlanner vehicle={hydrogenVehicle} />);

    const fullFill = screen.getByRole("radio", { name: "가득 충전 원칙" });
    expect(fullFill).toBeChecked();
    expect(fullFill).toBeDisabled();
    expect(screen.queryByRole("radio", { name: "필요한 만큼 충전" })).not.toBeInTheDocument();
    expect(screen.getByText(/차량 탱크 사양, 충전기 압력과 충전소 저장 탱크 잔량/)).toBeInTheDocument();
  });
});
