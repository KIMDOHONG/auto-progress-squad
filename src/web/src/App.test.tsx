import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { StrictMode } from "react";
import App from "./App";

describe("vehicle-aware planner", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    window.localStorage.clear();
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("shows the hydrogen planner for the default NEXO profile", () => {
    render(<App />);
    expect(screen.getByRole("option", { name: "현대 넥쏘 · 2021" })).toBeInTheDocument();
    const plannerButtons = screen.getAllByRole("button", { name: /수소 충전 플래너/ });
    expect(plannerButtons).toHaveLength(2);
    fireEvent.click(plannerButtons[0]);
    expect(screen.getByRole("heading", { name: "수소 충전·주행 플래너" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("수소")).toBeInTheDocument();
    expect(screen.getByText("경로 수소충전소 A")).toBeInTheDocument();
  });

  it("switches to the EV planner for the IONIQ 5 N profile", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("활성 차량"), { target: { value: "sample-ioniq5n" } });
    const plannerButtons = await screen.findAllByRole("button", { name: /EV 충전 플래너/ });
    expect(plannerButtons).toHaveLength(2);
    fireEvent.click(plannerButtons[0]);
    expect(screen.getByLabelText("목적지")).toHaveValue("대한상공회의소 부산인력개발원");
  });

  it("switches to the fuel planner for a combustion vehicle", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("활성 차량"), { target: { value: "sample-bmwm3" } });
    const plannerButtons = await screen.findAllByRole("button", { name: /주유 경로 플래너/ });
    expect(plannerButtons).toHaveLength(2);
    fireEvent.click(plannerButtons[0]);
    expect(await screen.findByText("BMW M3 · 2021 · 고급 휘발유 우선 검색")).toBeInTheDocument();
  });

  it("edits an existing vehicle profile", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "차량 프로필 관리" }));
    const dialog = within(screen.getByRole("dialog", { name: "내 차량 관리" }));
    fireEvent.click(dialog.getAllByRole("button", { name: "수정" })[2]);
    fireEvent.change(dialog.getByRole("textbox", { name: "모델 *" }), { target: { value: "M3 Competition" } });
    fireEvent.click(dialog.getByRole("button", { name: "변경 저장" }));
    expect(await screen.findByRole("option", { name: "BMW M3 Competition · 2021" })).toBeInTheDocument();
  });

  it("migrates the unchanged v1 demo presets to the new three-vehicle set", () => {
    window.localStorage.setItem("auto-squad.vehicle-profiles.v1", JSON.stringify({
      version: 1,
      vehicles: [
        { id: "sample-ioniq5", nickname: "출퇴근 EV", manufacturer: "현대", model: "아이오닉 5", modelYear: 2024, powertrain: "electric", batteryCapacityKwh: 84 },
        { id: "sample-bmw3", nickname: "주말 차량", manufacturer: "BMW", model: "330i", modelYear: 2022, powertrain: "gasoline", fuelGrade: "premium" },
      ],
      activeVehicleId: "sample-ioniq5",
    }));

    render(<App />);

    expect(screen.getAllByRole("option")).toHaveLength(3);
    expect(screen.getByRole("option", { name: "현대 넥쏘 · 2021" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "현대 아이오닉 5 N · 2024" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "BMW M3 · 2021" })).toBeInTheDocument();
    expect(window.localStorage.getItem("auto-squad.vehicle-profiles.v1")).toBeNull();
  });

  it("loads vehicle profiles from the configured FastAPI backend", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:8000");
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [{
          id: "api-bmw",
          nickname: "API 차량",
          manufacturer: "BMW",
          model: "330i",
          model_year: 2023,
          powertrain: "gasoline",
          fuel_grade: "premium",
          battery_capacity_kwh: null,
          is_active: true,
        }],
        active_vehicle_id: "api-bmw",
      }),
    } as Response);

    render(<StrictMode><App /></StrictMode>);

    expect(await screen.findByRole("option", { name: "BMW 330i · 2023" })).toBeInTheDocument();
    expect(screen.getByText("SQLite 동기화")).toBeInTheDocument();
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/vehicles",
      expect.any(Object),
    ));
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });
});
