import type { FuelGrade, Powertrain, VehicleProfile } from "../types";

export const POWERTRAIN_LABELS: Record<Powertrain, string> = {
  electric: "전기차",
  gasoline: "가솔린",
  diesel: "디젤",
  hybrid: "하이브리드",
};

export const FUEL_GRADE_LABELS: Record<FuelGrade, string> = {
  regular: "일반 휘발유",
  premium: "고급 휘발유",
  "super-premium": "초고급 휘발유",
  diesel: "일반 경유",
  "high-cetane": "하이세탄 경유",
};

export const DEFAULT_VEHICLES: VehicleProfile[] = [
  {
    id: "sample-ioniq5",
    nickname: "출퇴근 EV",
    manufacturer: "현대",
    model: "아이오닉 5",
    modelYear: 2024,
    powertrain: "electric",
    batteryCapacityKwh: 84,
  },
  {
    id: "sample-bmw3",
    nickname: "주말 차량",
    manufacturer: "BMW",
    model: "330i",
    modelYear: 2022,
    powertrain: "gasoline",
    fuelGrade: "premium",
  },
];

export function getVehicleTitle(vehicle: VehicleProfile): string {
  return `${vehicle.manufacturer} ${vehicle.model} · ${vehicle.modelYear}`;
}

export function isEv(vehicle: VehicleProfile): boolean {
  return vehicle.powertrain === "electric";
}

export function getEnergyLabel(vehicle: VehicleProfile): string {
  if (isEv(vehicle)) return "전기 충전";
  return vehicle.fuelGrade ? FUEL_GRADE_LABELS[vehicle.fuelGrade] : POWERTRAIN_LABELS[vehicle.powertrain];
}
