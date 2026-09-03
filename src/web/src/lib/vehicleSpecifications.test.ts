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

  it("keeps adjacent model years out of the automatic match", () => {
    expect(findVehicleSpecifications("기아", "EV6", 2026, "electric")).toEqual([]);
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
});
