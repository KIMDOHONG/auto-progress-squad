import { ENERGY_STORAGE_DEFINITIONS, findVehicleSpecifications, resolveVehicleSpecification } from "./vehicleSpecifications";

describe("verified vehicle specification catalog", () => {
  it("resolves an exact 2027 EV6 configuration and battery capacity", () => {
    const result = resolveVehicleSpecification(
      "KIA",
      "더 뉴 EV6",
      2027,
      "electric",
      "롱레인지 4WD",
      "GT-Line",
    );

    expect(result).toEqual(expect.objectContaining({
      id: "kia-ev6-2027-long-range-4wd",
      batteryCapacityKwh: 84,
    }));
  });

  it("resolves the official 2026 EV6 long-range 4WD configuration", () => {
    const result = resolveVehicleSpecification(
      "기아",
      "EV6",
      2026,
      "electric",
      "롱레인지 4WD",
      "GT LINE",
    );

    expect(result).toEqual(expect.objectContaining({
      id: "kia-ev6-2026-long-range-4wd",
      batteryCapacityKwh: 84,
      sourceUrl: "https://www.kia.com/kr/vehicles/ev6/specification",
    }));
  });

  it("keeps unverified pre-facelift EV6 years out of the automatic match", () => {
    expect(findVehicleSpecifications("기아", "EV6", 2024, "electric")).toEqual([]);
  });

  it("does not accept a trim that is unavailable for the selected configuration", () => {
    expect(resolveVehicleSpecification(
      "기아",
      "EV6",
      2027,
      "electric",
      "스탠다드 2WD",
      "GT-Line",
    )).toBeUndefined();
  });

  it("keeps previously saved Genesis configuration labels compatible", () => {
    expect(resolveVehicleSpecification(
      "제네시스",
      "ELECTRIFIED GV70",
      2027,
      "electric",
      "듀얼모터 AWD",
      "기본형",
    )).toEqual(expect.objectContaining({
      id: "genesis-electrified-gv70-2027-awd",
      batteryCapacityKwh: 84,
    }));
  });

  it.each([
    ["현대", "아이오닉 5", 2027, "롱레인지 AWD", 84],
    ["현대", "아이오닉 6", 2025, "롱레인지 2WD", 77.4],
    ["현대", "아이오닉 9", 2027, "성능형 AWD", 110.3],
    ["현대", "코나 EV", 2025, "스탠다드 2WD", 48.6],
    ["기아", "EV3", 2026, "롱레인지 2WD", 81.4],
    ["기아", "EV4", 2027, "스탠다드 2WD", 58.3],
    ["기아", "EV3", 2026, "롱레인지 4WD", 81.4],
    ["기아", "EV4", 2026, "스탠다드 4WD", 58.3],
    ["기아", "EV5", 2026, "스탠다드 2WD", 60.3],
    ["기아", "EV5", 2026, "롱레인지 4WD", 81.4],
    ["기아", "EV4 GT", 2026, "GT 4WD", 81.4],
    ["기아", "EV9 GT", 2026, "GT 4WD", 99.8],
    ["기아", "EV9", 2027, "롱레인지 4WD", 99.8],
    ["기아", "니로 EV", 2026, "2WD", 64.8],
    ["기아", "니로 플러스", 2023, "2WD", 64],
    ["제네시스", "GV60", 2027, "퍼포먼스 AWD", 84],
    ["제네시스", "EG80", 2027, "듀얼 모터 AWD", 94.5],
  ])("maps %s %s %i %s without duplicating trim-specific capacity", (manufacturer, model, year, detail, capacity) => {
    expect(resolveVehicleSpecification(manufacturer as string, model as string, year as number, "electric", detail as string, "사용자 실제 트림")).toEqual(expect.objectContaining({
      batteryCapacityKwh: capacity,
    }));
  });

  it("stores the shared Kia 81.4 kWh definition only once", () => {
    expect(ENERGY_STORAGE_DEFINITIONS["kia-81.4"]).toEqual(expect.objectContaining({ batteryCapacityKwh: 81.4 }));
    expect(Object.values(ENERGY_STORAGE_DEFINITIONS).filter((item) => item.batteryCapacityKwh === 81.4)).toHaveLength(1);
  });

  it("maps the 2025 K5 gasoline powertrain to its official 60 L tank", () => {
    expect(resolveVehicleSpecification(
      "기아",
      "더 뉴 K5",
      2025,
      "gasoline",
      "1.6 가솔린 터보",
      "노블레스",
    )).toEqual(expect.objectContaining({
      id: "kia-k5-gasoline-2025-1.6-t-gdi",
      fuelTankCapacityLiters: 60,
      sourceUrl: "https://ownersmanual.kia.com/full_webhelp/DL3/2025/ko_KR/topics/chapter9_5.html",
    }));
  });

  it("keeps the K5 hybrid tank separate from the gasoline model", () => {
    expect(resolveVehicleSpecification(
      "KIA",
      "K5 하이브리드",
      2026,
      "hybrid",
      "2.0 하이브리드",
      "시그니처",
    )).toEqual(expect.objectContaining({
      id: "kia-k5-hybrid-2026-2.0-hybrid",
      fuelTankCapacityLiters: 50,
      sourceUrl: "https://ownersmanual.kia.com/full_webhelp/DL3KH/2026/ko_KR/topics/chapter9_5.html",
    }));
    expect(ENERGY_STORAGE_DEFINITIONS["kia-fuel-50"].fuelTankCapacityLiters).toBe(50);
    expect(ENERGY_STORAGE_DEFINITIONS["kia-fuel-60"].fuelTankCapacityLiters).toBe(60);
  });

  it("does not infer a tank for an unverified model year or mismatched powertrain", () => {
    expect(findVehicleSpecifications("기아", "K5", 2027, "gasoline")).toEqual([]);
    expect(findVehicleSpecifications("기아", "K5", 2026, "diesel")).toEqual([]);
  });
});
