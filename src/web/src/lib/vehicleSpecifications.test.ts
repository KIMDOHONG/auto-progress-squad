import { findVehicleSpecifications, resolveVehicleSpecification } from "./vehicleSpecifications";

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
      sourceUrl: "https://kwp1.kia.com/content/dam/kwp/kr/ko/vehicles/pdf/catalog/catalog_ev6.pdf",
    }));
  });

  it("keeps adjacent model years out of the automatic match", () => {
    expect(findVehicleSpecifications("기아", "EV6", 2025, "electric")).toEqual([]);
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
});
