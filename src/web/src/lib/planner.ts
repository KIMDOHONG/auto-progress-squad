export type PlannerStatus = "sufficient" | "stop-required";

export interface PlannerValidationFailure {
  ok: false;
  errors: string[];
}

export interface EvPlannerInput {
  routeDistanceKm: number;
  batteryCapacityKwh: number;
  currentSocPercent: number;
  efficiencyKmPerKwh: number;
  minimumArrivalSocPercent: number;
}

export interface EvPlannerResult {
  ok: true;
  kind: "electric";
  status: PlannerStatus;
  routeDistanceKm: number;
  batteryCapacityKwh: number;
  currentSocPercent: number;
  efficiencyKmPerKwh: number;
  minimumArrivalSocPercent: number;
  currentEnergyKwh: number;
  tripEnergyKwh: number;
  reserveEnergyKwh: number;
  arrivalSocWithoutChargePercent: number;
  availableDistanceToReserveKm: number;
  requiredChargeKwh: number;
}

export interface RangePlannerInput {
  routeDistanceKm: number;
  remainingRangeKm: number;
  kind: "hydrogen" | "fuel";
}

export interface RangePlannerResult {
  ok: true;
  kind: "hydrogen" | "fuel";
  status: PlannerStatus;
  routeDistanceKm: number;
  remainingRangeKm: number;
  remainingMarginKm: number;
  requiredAdditionalRangeKm: number;
}

export type EvPlannerCalculation = EvPlannerResult | PlannerValidationFailure;
export type RangePlannerCalculation = RangePlannerResult | PlannerValidationFailure;

function round(value: number): number {
  return Math.round((value + Number.EPSILON) * 10) / 10;
}

function isFiniteNumber(value: number): boolean {
  return Number.isFinite(value);
}

export function calculateEvPlan(input: EvPlannerInput): EvPlannerCalculation {
  const errors: string[] = [];

  if (!isFiniteNumber(input.routeDistanceKm) || input.routeDistanceKm <= 0) {
    errors.push("경로 거리는 0보다 큰 값이어야 합니다.");
  }
  if (!isFiniteNumber(input.batteryCapacityKwh) || input.batteryCapacityKwh <= 0) {
    errors.push("사용 가능 배터리 용량을 입력해 주세요.");
  }
  if (!isFiniteNumber(input.currentSocPercent) || input.currentSocPercent < 0 || input.currentSocPercent > 100) {
    errors.push("현재 SoC는 0%에서 100% 사이여야 합니다.");
  }
  if (!isFiniteNumber(input.efficiencyKmPerKwh) || input.efficiencyKmPerKwh <= 0) {
    errors.push("전비는 0보다 큰 값이어야 합니다.");
  }
  if (!isFiniteNumber(input.minimumArrivalSocPercent) || input.minimumArrivalSocPercent < 0 || input.minimumArrivalSocPercent > 100) {
    errors.push("도착 최소 SoC는 0%에서 100% 사이여야 합니다.");
  }

  if (errors.length > 0) return { ok: false, errors };

  const currentEnergyKwh = input.batteryCapacityKwh * input.currentSocPercent / 100;
  const tripEnergyKwh = input.routeDistanceKm / input.efficiencyKmPerKwh;
  const reserveEnergyKwh = input.batteryCapacityKwh * input.minimumArrivalSocPercent / 100;
  const arrivalSocWithoutChargePercent = input.currentSocPercent - tripEnergyKwh / input.batteryCapacityKwh * 100;
  const availableSocPercent = Math.max(0, input.currentSocPercent - input.minimumArrivalSocPercent);
  const availableDistanceToReserveKm = input.batteryCapacityKwh * availableSocPercent / 100 * input.efficiencyKmPerKwh;
  const requiredChargeKwh = Math.max(0, tripEnergyKwh + reserveEnergyKwh - currentEnergyKwh);

  return {
    ok: true,
    kind: "electric",
    status: requiredChargeKwh > 0 ? "stop-required" : "sufficient",
    routeDistanceKm: round(input.routeDistanceKm),
    batteryCapacityKwh: round(input.batteryCapacityKwh),
    currentSocPercent: round(input.currentSocPercent),
    efficiencyKmPerKwh: round(input.efficiencyKmPerKwh),
    minimumArrivalSocPercent: round(input.minimumArrivalSocPercent),
    currentEnergyKwh: round(currentEnergyKwh),
    tripEnergyKwh: round(tripEnergyKwh),
    reserveEnergyKwh: round(reserveEnergyKwh),
    arrivalSocWithoutChargePercent: round(arrivalSocWithoutChargePercent),
    availableDistanceToReserveKm: round(availableDistanceToReserveKm),
    requiredChargeKwh: round(requiredChargeKwh),
  };
}

export function calculateRangePlan(input: RangePlannerInput): RangePlannerCalculation {
  const errors: string[] = [];

  if (!isFiniteNumber(input.routeDistanceKm) || input.routeDistanceKm <= 0) {
    errors.push("경로 거리는 0보다 큰 값이어야 합니다.");
  }
  if (!isFiniteNumber(input.remainingRangeKm) || input.remainingRangeKm < 0) {
    errors.push("현재 주행가능거리는 0 이상의 값이어야 합니다.");
  }

  if (errors.length > 0) return { ok: false, errors };

  const remainingMarginKm = input.remainingRangeKm - input.routeDistanceKm;

  return {
    ok: true,
    kind: input.kind,
    status: remainingMarginKm >= 0 ? "sufficient" : "stop-required",
    routeDistanceKm: round(input.routeDistanceKm),
    remainingRangeKm: round(input.remainingRangeKm),
    remainingMarginKm: round(Math.max(0, remainingMarginKm)),
    requiredAdditionalRangeKm: round(Math.max(0, -remainingMarginKm)),
  };
}
