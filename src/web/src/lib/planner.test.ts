import { calculateEvPlan, calculateRangePlan } from "./planner";

describe("calculateEvPlan", () => {
  it("marks a route as sufficient when the minimum arrival SoC is preserved", () => {
    const result = calculateEvPlan({
      routeDistanceKm: 100,
      batteryCapacityKwh: 84,
      currentSocPercent: 42,
      efficiencyKmPerKwh: 5.1,
      minimumArrivalSocPercent: 10,
    });

    expect(result).toEqual({
      ok: true,
      kind: "electric",
      status: "sufficient",
      routeDistanceKm: 100,
      batteryCapacityKwh: 84,
      currentSocPercent: 42,
      efficiencyKmPerKwh: 5.1,
      minimumArrivalSocPercent: 10,
      currentEnergyKwh: 35.3,
      tripEnergyKwh: 19.6,
      reserveEnergyKwh: 8.4,
      arrivalSocWithoutChargePercent: 18.7,
      availableDistanceToReserveKm: 137.1,
      requiredChargeKwh: 0,
    });
  });

  it("calculates the minimum charge needed to preserve the arrival reserve", () => {
    const result = calculateEvPlan({
      routeDistanceKm: 250,
      batteryCapacityKwh: 84,
      currentSocPercent: 42,
      efficiencyKmPerKwh: 5.1,
      minimumArrivalSocPercent: 10,
    });

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.status).toBe("stop-required");
    expect(result.tripEnergyKwh).toBe(49);
    expect(result.arrivalSocWithoutChargePercent).toBe(-16.4);
    expect(result.requiredChargeKwh).toBe(22.1);
  });

  it("allows a minimum arrival SoC above the current SoC and reports charging required", () => {
    const result = calculateEvPlan({
      routeDistanceKm: 10,
      batteryCapacityKwh: 80,
      currentSocPercent: 20,
      efficiencyKmPerKwh: 5,
      minimumArrivalSocPercent: 30,
    });

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.status).toBe("stop-required");
    expect(result.availableDistanceToReserveKm).toBe(0);
    expect(result.requiredChargeKwh).toBe(10);
  });

  it("returns every relevant validation error instead of calculating with invalid values", () => {
    expect(calculateEvPlan({
      routeDistanceKm: 0,
      batteryCapacityKwh: Number.NaN,
      currentSocPercent: 101,
      efficiencyKmPerKwh: 0,
      minimumArrivalSocPercent: -1,
    })).toEqual({
      ok: false,
      errors: [
        "경로 거리는 0보다 큰 값이어야 합니다.",
        "사용 가능 배터리 용량을 입력해 주세요.",
        "현재 SoC는 0%에서 100% 사이여야 합니다.",
        "전비는 0보다 큰 값이어야 합니다.",
        "도착 최소 SoC는 0%에서 100% 사이여야 합니다.",
      ],
    });
  });
});

describe("calculateRangePlan", () => {
  it("reports the remaining margin for a reachable hydrogen route", () => {
    expect(calculateRangePlan({ kind: "hydrogen", routeDistanceKm: 100, remainingRangeKm: 120 })).toEqual({
      ok: true,
      kind: "hydrogen",
      status: "sufficient",
      routeDistanceKm: 100,
      remainingRangeKm: 120,
      remainingMarginKm: 20,
      requiredAdditionalRangeKm: 0,
    });
  });

  it("treats an exact range match as reachable", () => {
    const result = calculateRangePlan({ kind: "fuel", routeDistanceKm: 120, remainingRangeKm: 120 });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.status).toBe("sufficient");
    expect(result.remainingMarginKm).toBe(0);
  });

  it("reports the additional range required for an unreachable fuel route", () => {
    const result = calculateRangePlan({ kind: "fuel", routeDistanceKm: 180, remainingRangeKm: 120 });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.status).toBe("stop-required");
    expect(result.requiredAdditionalRangeKm).toBe(60);
  });

  it("rejects an invalid route distance and remaining range", () => {
    expect(calculateRangePlan({ kind: "hydrogen", routeDistanceKm: -1, remainingRangeKm: -1 })).toEqual({
      ok: false,
      errors: [
        "경로 거리는 0보다 큰 값이어야 합니다.",
        "현재 주행가능거리는 0 이상의 값이어야 합니다.",
      ],
    });
  });
});
