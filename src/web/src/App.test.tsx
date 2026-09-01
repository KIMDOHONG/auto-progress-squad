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

  it("switches to the EV planner for the ELECTRIFIED GV70 profile", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("활성 차량"), { target: { value: "sample-electrified-gv70" } });
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
    expect(screen.getByRole("option", { name: "제네시스 ELECTRIFIED GV70 · 2027" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "BMW M3 · 2021" })).toBeInTheDocument();
    expect(window.localStorage.getItem("auto-squad.vehicle-profiles.v1")).toBeNull();
  });

  it("replaces the unchanged v2 IONIQ 5 N demo preset", () => {
    window.localStorage.setItem("auto-squad.vehicle-profiles.v2", JSON.stringify({
      version: 2,
      vehicles: [
        { id: "sample-nexo", nickname: "가족 수소차", manufacturer: "현대", model: "넥쏘", modelYear: 2021, powertrain: "hydrogen" },
        { id: "sample-ioniq5n", nickname: "고성능 EV", manufacturer: "현대", model: "아이오닉 5 N", modelYear: 2024, powertrain: "electric", batteryCapacityKwh: 84 },
        { id: "sample-bmwm3", nickname: "주말 차량", manufacturer: "BMW", model: "M3", modelYear: 2021, powertrain: "gasoline", fuelGrade: "premium" },
      ],
      activeVehicleId: "sample-ioniq5n",
    }));

    render(<App />);

    expect(screen.getByRole("option", { name: "제네시스 ELECTRIFIED GV70 · 2027" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "현대 아이오닉 5 N · 2024" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("활성 차량")).toHaveValue("sample-electrified-gv70");
    expect(window.localStorage.getItem("auto-squad.vehicle-profiles.v2")).toBeNull();
  });

  it("preserves customized v2 profiles during the storage migration", () => {
    window.localStorage.setItem("auto-squad.vehicle-profiles.v2", JSON.stringify({
      version: 2,
      vehicles: [
        { id: "custom-car", nickname: "내 차", manufacturer: "기아", model: "K5", modelYear: 2025, powertrain: "gasoline", fuelGrade: "regular" },
      ],
      activeVehicleId: "custom-car",
    }));

    render(<App />);

    expect(screen.getAllByRole("option")).toHaveLength(1);
    expect(screen.getByRole("option", { name: "기아 K5 · 2025" })).toBeInTheDocument();
    expect(window.localStorage.getItem("auto-squad.vehicle-profiles.v2")).toBeNull();
  });

  it("opens the exact Genesis manual for the active model and year", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("활성 차량"), { target: { value: "sample-electrified-gv70" } });
    fireEvent.click(screen.getByRole("button", { name: "매뉴얼·리콜" }));

    const manualLink = await screen.findByRole("link", { name: /공식 취급설명서 열기/ });
    expect(manualLink).toHaveAttribute(
      "href",
      "https://ownersmanual.genesis.com/manual/ELECTRIFIED%20GV70?projCode=JKEV&year=2027&langCode=ko_KR&countryCode=A99",
    );
    expect(screen.getByText(/JKEV · 2027/)).toBeInTheDocument();
  });

  it("does not guess a BMW manual before a VIN is available", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("활성 차량"), { target: { value: "sample-bmwm3" } });
    fireEvent.click(screen.getByRole("button", { name: "매뉴얼·리콜" }));

    expect(await screen.findByText("VIN 확인 필요")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /공식 취급설명서 열기/ })).not.toBeInTheDocument();
    expect(screen.getByText(/BMW M3 · 2021의 정확한 취급설명서/)).toBeInTheDocument();
    expect(screen.queryByText(/G80 M3/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /BMW Driver's Guide 열기/ })).toHaveAttribute(
      "href",
      "https://www.bmw.co.kr/ko/topics/owners/online-manual/bmw-driver-guide.html",
    );
  });

  it("shows the verified official vehicle image in the manual heading", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "매뉴얼·리콜" }));

    const image = await screen.findByRole("img", { name: "현대 넥쏘 · 2021 공식 차량 이미지" });
    expect(image).toHaveAttribute(
      "src",
      "https://ownersmanual.hyundai.com/api/v2/hmc/files/6406/H_FE_2024.png",
    );
  });

  it("registers a selected 2020 K5 generation from official chat candidates", async () => {
    window.localStorage.setItem("auto-squad.vehicle-profiles.v4", JSON.stringify({
      version: 4,
      vehicles: [{ id: "only-car", nickname: "기존 차량", manufacturer: "BMW", model: "M3", modelYear: 2021, powertrain: "gasoline", fuelGrade: "premium" }],
      activeVehicleId: "only-car",
    }));
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("ownersmanual.kia.com") && url.includes("/models")) {
        return { ok: true, status: 200, json: async () => ({ CARS: [{ langModelName: "K5" }] }) } as Response;
      }
      if (url.includes("ownersmanual.kia.com") && url.includes("/model?")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            years: ["2020"],
            yearModels: {
              "2020": [
                { modelName: "K5", projCode: "DL3", year: "2020", fuel: "ICE", mainImgUrl: "/api/v2/kia/files/2309/DLSD20SWP.png" },
                { modelName: "K5", projCode: "JF", year: "2020", fuel: "ICE", mainImgUrl: "/api/v2/kia/files/2582/KFSD19SWP.png" },
              ],
            },
          }),
        } as Response;
      }
      if (url.includes("/models")) {
        return { ok: true, status: 200, json: async () => ({ CARS: [] }) } as Response;
      }
      throw new Error(`unexpected request: ${url}`);
    }) as typeof fetch;

    render(<App />);
    fireEvent.change(screen.getByLabelText("AI 코파일럿에게 메시지 보내기"), { target: { value: "2020 K5 등록" } });
    fireEvent.click(screen.getByRole("button", { name: "메시지 전송" }));

    expect(await screen.findByText("같은 연식에 여러 세대가 있어 차량 이미지를 보고 선택해 주세요.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "2020 K5 JF 선택" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "2020 K5 DL3 선택" }));
    fireEvent.click(await screen.findByRole("button", { name: "프로필 등록" }));

    expect(await screen.findByRole("option", { name: "기아 K5 · 2020" })).toBeInTheDocument();
    expect(screen.getByText(/DL3\) 프로필을 등록하고 활성 차량으로 변경했습니다/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "매뉴얼·리콜" }));
    expect(await screen.findByText(/DL3 · 2020/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "기아 K5 · 2020 공식 차량 이미지" })).toHaveAttribute("src", "https://ownersmanual.kia.com/api/v2/kia/files/2309/DLSD20SWP.png");
  });

  it("asks which existing profile to replace when all three slots are occupied", async () => {
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("ownersmanual.kia.com") && url.includes("/models")) {
        return { ok: true, status: 200, json: async () => ({ CARS: [{ langModelName: "K5" }] }) } as Response;
      }
      if (url.includes("ownersmanual.kia.com") && url.includes("/model?")) {
        return { ok: true, status: 200, json: async () => ({ years: ["2020"], yearModels: { "2020": [
          { modelName: "K5", projCode: "DL3", year: "2020", fuel: "ICE", mainImgUrl: "/api/v2/kia/files/2309/DLSD20SWP.png" },
          { modelName: "K5", projCode: "JF", year: "2020", fuel: "ICE", mainImgUrl: "/api/v2/kia/files/2582/KFSD19SWP.png" },
        ] } }) } as Response;
      }
      if (url.includes("/models")) return { ok: true, status: 200, json: async () => ({ CARS: [] }) } as Response;
      throw new Error(`unexpected request: ${url}`);
    }) as typeof fetch;

    render(<App />);
    fireEvent.change(screen.getByLabelText("AI 코파일럿에게 메시지 보내기"), { target: { value: "2020 기아 K5 등록" } });
    fireEvent.click(screen.getByRole("button", { name: "메시지 전송" }));
    fireEvent.click(await screen.findByRole("button", { name: "2020 K5 DL3 선택" }));
    fireEvent.click(await screen.findByRole("button", { name: "기존 차량 교체 후 등록" }));

    expect(await screen.findAllByText(/현재 프로필이 3대이고 최대 3대까지 등록할 수 있습니다/)).toHaveLength(2);
    fireEvent.click(screen.getByText("주말 차량").closest("button") as HTMLButtonElement);
    fireEvent.click(await screen.findByRole("button", { name: "삭제하고 등록" }));

    expect(await screen.findByRole("option", { name: "기아 K5 · 2020" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "BMW M3 · 2021" })).not.toBeInTheDocument();
    expect(within(screen.getByLabelText("활성 차량")).getAllByRole("option")).toHaveLength(3);
  });

  it("deletes a named profile only after chat confirmation", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("AI 코파일럿에게 메시지 보내기"), { target: { value: "주말 차량 프로필 삭제" } });
    fireEvent.click(screen.getByRole("button", { name: "메시지 전송" }));

    expect(await screen.findByText("주말 차량 · BMW M3 · 2021")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "프로필 삭제" }));

    await waitFor(() => expect(screen.queryByRole("option", { name: "BMW M3 · 2021" })).not.toBeInTheDocument());
    expect(screen.getByText(/주말 차량 · BMW M3 · 2021 프로필을 삭제했습니다/)).toBeInTheDocument();
  });

  it("uses the active vehicle for a generic recall request", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("AI 코파일럿에게 메시지 보내기"), { target: { value: "내 차 리콜 확인해줘" } });
    fireEvent.click(screen.getByRole("button", { name: "메시지 전송" }));

    expect(await screen.findByText(/현재 활성 차량인 가족 수소차 · 현대 넥쏘 · 2021 프로필을 리콜 조회 대상으로 확인했습니다/)).toBeInTheDocument();
  });

  it("uses an explicitly named registered vehicle instead of the active vehicle for recall", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("AI 코파일럿에게 메시지 보내기"), { target: { value: "2021 BMW M3 리콜 확인" } });
    fireEvent.click(screen.getByRole("button", { name: "메시지 전송" }));

    expect(await screen.findByText(/질문에 명시한 등록 차량인 주말 차량 · BMW M3 · 2021 프로필을 리콜 조회 대상으로 확인했습니다/)).toBeInTheDocument();
    expect(screen.queryByText(/현대 넥쏘 · 2021 프로필을 리콜 조회 대상으로/)).not.toBeInTheDocument();
  });

  it("does not substitute the active vehicle when an explicit recall vehicle is not registered", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("AI 코파일럿에게 메시지 보내기"), { target: { value: "2025 K5 리콜" } });
    fireEvent.click(screen.getByRole("button", { name: "메시지 전송" }));

    expect(await screen.findByText(/‘2025 K5’ 차량과 일치하는 등록 프로필을 찾지 못했습니다/)).toBeInTheDocument();
    expect(screen.queryByText(/현대 넥쏘 · 2021 프로필을 리콜 조회 대상으로/)).not.toBeInTheDocument();
  });

  it("explains that BMW was recognized but its manual was not searched", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("AI 코파일럿에게 메시지 보내기"), { target: { value: "2015 BMW M3 등록" } });
    fireEvent.click(screen.getByRole("button", { name: "메시지 전송" }));

    expect(await screen.findByText(/BMW 공식 설명서는 아직 조회하지 않았습니다/)).toBeInTheDocument();
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
