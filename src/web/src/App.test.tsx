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

  it("shows the EV planner for an electric active vehicle", () => {
    render(<App />);
    const plannerButtons = screen.getAllByRole("button", { name: /EV 충전 플래너/ });
    expect(plannerButtons).toHaveLength(2);
    fireEvent.click(plannerButtons[0]);
    expect(screen.getByLabelText("목적지")).toHaveValue("대한상공회의소 부산인력개발원");
  });

  it("switches to the fuel planner for a combustion vehicle", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("활성 차량"), { target: { value: "sample-bmw3" } });
    const plannerButtons = await screen.findAllByRole("button", { name: /주유 경로 플래너/ });
    expect(plannerButtons).toHaveLength(2);
    fireEvent.click(plannerButtons[0]);
    expect(await screen.findByText("BMW 330i · 2022 · 고급 휘발유 우선 검색")).toBeInTheDocument();
  });

  it("edits an existing vehicle profile", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "차량 프로필 관리" }));
    const dialog = within(screen.getByRole("dialog", { name: "내 차량 관리" }));
    fireEvent.click(dialog.getAllByRole("button", { name: "수정" })[1]);
    fireEvent.change(dialog.getByRole("textbox", { name: "모델 *" }), { target: { value: "330i M Sport" } });
    fireEvent.click(dialog.getByRole("button", { name: "변경 저장" }));
    expect(await screen.findByRole("option", { name: "BMW 330i M Sport · 2022" })).toBeInTheDocument();
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
