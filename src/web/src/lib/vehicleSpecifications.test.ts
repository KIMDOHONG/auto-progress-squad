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
});
