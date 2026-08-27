import type { FuelGrade, Powertrain, VehicleProfile } from "../types";

export const POWERTRAIN_LABELS: Record<Powertrain, string> = {
  electric: "전기차",
  hydrogen: "수소전기차",
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
    id: "sample-nexo",
    nickname: "가족 수소차",
    manufacturer: "현대",
    model: "넥쏘",
    modelYear: 2021,
    powertrain: "hydrogen",
    manual: {
      siteId: "hmc",
      modelName: "넥쏘",
      projectCode: "FE",
      modelYear: 2021,
      imageUrl: "https://ownersmanual.hyundai.com/api/v2/hmc/files/6406/H_FE_2024.png",
      verifiedAt: "2026-08-27T00:00:00.000Z",
    },
  },
  {
    id: "sample-electrified-gv70",
    nickname: "프리미엄 EV",
    manufacturer: "제네시스",
    model: "ELECTRIFIED GV70",
    modelYear: 2027,
    powertrain: "electric",
    batteryCapacityKwh: 84,
    manual: {
      siteId: "genesis",
      modelName: "ELECTRIFIED GV70",
      projectCode: "JKEV",
      modelYear: 2027,
      imageUrl: "https://ownersmanual.genesis.com/api/v2/genesis/files/6295/JK1EV-CeresBlue-MSA-01-18F-630x240.png",
      verifiedAt: "2026-08-27T00:00:00.000Z",
    },
  },
  {
    id: "sample-bmwm3",
    nickname: "주말 차량",
    manufacturer: "BMW",
    model: "M3",
    modelYear: 2021,
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

export function isHydrogen(vehicle: VehicleProfile): boolean {
  return vehicle.powertrain === "hydrogen";
}

export function getEnergyLabel(vehicle: VehicleProfile): string {
  if (isEv(vehicle)) return "전기 충전";
  if (isHydrogen(vehicle)) return "수소 충전";
  return vehicle.fuelGrade ? FUEL_GRADE_LABELS[vehicle.fuelGrade] : POWERTRAIN_LABELS[vehicle.powertrain];
}
