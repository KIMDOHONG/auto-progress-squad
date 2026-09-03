import type { Powertrain } from "../types";

export interface VehicleSpecification {
  id: string;
  manufacturer: string;
  manufacturerAliases: string[];
  model: string;
  modelAliases: string[];
  modelYear: number;
  powertrain: Powertrain;
  powertrainDetail: string;
  trims: string[];
  batteryCapacityKwh?: number;
  sourceUrl: string;
  verifiedAt: string;
}

const KIA_EV6_SOURCE = "https://www.kia.com/kr/vehicles/ev6/price";
const HYUNDAI_KONA_EV_SOURCE = "https://www.hyundai.com/contents/repn-car/catalog/kona-electric-2025-price.pdf";
const GENESIS_EGV70_SOURCE = "https://www.genesis.com/kr/ko/models/electrified-gv70";

export const VEHICLE_SPECIFICATIONS: VehicleSpecification[] = [
  {
    id: "kia-ev6-2027-standard-2wd",
    manufacturer: "기아",
    manufacturerAliases: ["기아", "KIA"],
    model: "EV6",
    modelAliases: ["EV6", "더 뉴 EV6"],
    modelYear: 2027,
    powertrain: "electric",
    powertrainDetail: "스탠다드 2WD",
    trims: ["라이트", "에어", "어스"],
    batteryCapacityKwh: 63,
    sourceUrl: KIA_EV6_SOURCE,
    verifiedAt: "2026-09-03",
  },
  {
    id: "kia-ev6-2027-long-range-2wd",
    manufacturer: "기아",
    manufacturerAliases: ["기아", "KIA"],
    model: "EV6",
    modelAliases: ["EV6", "더 뉴 EV6"],
    modelYear: 2027,
    powertrain: "electric",
    powertrainDetail: "롱레인지 2WD",
    trims: ["라이트", "에어", "어스", "GT-Line"],
    batteryCapacityKwh: 84,
    sourceUrl: KIA_EV6_SOURCE,
    verifiedAt: "2026-09-03",
  },
  {
    id: "kia-ev6-2027-long-range-4wd",
    manufacturer: "기아",
    manufacturerAliases: ["기아", "KIA"],
    model: "EV6",
    modelAliases: ["EV6", "더 뉴 EV6"],
    modelYear: 2027,
    powertrain: "electric",
    powertrainDetail: "롱레인지 4WD",
    trims: ["라이트", "에어", "어스", "GT-Line"],
    batteryCapacityKwh: 84,
    sourceUrl: KIA_EV6_SOURCE,
    verifiedAt: "2026-09-03",
  },
  {
    id: "hyundai-kona-electric-2025-standard",
    manufacturer: "현대",
    manufacturerAliases: ["현대", "현대자동차", "HYUNDAI"],
    model: "코나 Electric",
    modelAliases: ["코나 ELECTRIC", "코나 일렉트릭", "디 올 뉴 코나", "THE ALL NEW KONA ELECTRIC"],
    modelYear: 2025,
    powertrain: "electric",
    powertrainDetail: "스탠다드 2WD",
    trims: ["E-Value +", "프리미엄"],
    batteryCapacityKwh: 48.6,
    sourceUrl: HYUNDAI_KONA_EV_SOURCE,
    verifiedAt: "2026-09-03",
  },
  {
    id: "hyundai-kona-electric-2025-long-range",
    manufacturer: "현대",
    manufacturerAliases: ["현대", "현대자동차", "HYUNDAI"],
    model: "코나 Electric",
    modelAliases: ["코나 ELECTRIC", "코나 일렉트릭", "디 올 뉴 코나", "THE ALL NEW KONA ELECTRIC"],
    modelYear: 2025,
    powertrain: "electric",
    powertrainDetail: "롱레인지 2WD",
    trims: ["모던 플러스", "프리미엄", "인스퍼레이션", "Black Exterior", "N Line"],
    batteryCapacityKwh: 64.8,
    sourceUrl: HYUNDAI_KONA_EV_SOURCE,
    verifiedAt: "2026-09-03",
  },
  {
    id: "genesis-electrified-gv70-2027-awd",
    manufacturer: "제네시스",
    manufacturerAliases: ["제네시스", "GENESIS"],
    model: "ELECTRIFIED GV70",
    modelAliases: ["ELECTRIFIED GV70", "GV70 전동화", "일렉트리파이드 GV70"],
    modelYear: 2027,
    powertrain: "electric",
    powertrainDetail: "듀얼모터 AWD",
    trims: ["기본형"],
    batteryCapacityKwh: 84,
    sourceUrl: GENESIS_EGV70_SOURCE,
    verifiedAt: "2026-09-03",
  },
];

function normalize(value: string): string {
  return value.toLocaleUpperCase("ko-KR").replace(/[^0-9A-Z가-힣]/g, "");
}

export function findVehicleSpecifications(
  manufacturer: string,
  model: string,
  modelYear: number,
  powertrain: Powertrain,
): VehicleSpecification[] {
  const normalizedManufacturer = normalize(manufacturer);
  const normalizedModel = normalize(model);
  if (!normalizedManufacturer || !normalizedModel || !Number.isInteger(modelYear)) return [];

  return VEHICLE_SPECIFICATIONS.filter((item) => (
    item.modelYear === modelYear
    && item.powertrain === powertrain
    && item.manufacturerAliases.some((alias) => normalize(alias) === normalizedManufacturer)
    && item.modelAliases.some((alias) => normalize(alias) === normalizedModel)
  ));
}

export function resolveVehicleSpecification(
  manufacturer: string,
  model: string,
  modelYear: number,
  powertrain: Powertrain,
  powertrainDetail: string,
  trim: string,
): VehicleSpecification | undefined {
  const normalizedDetail = normalize(powertrainDetail);
  const normalizedTrim = normalize(trim);
  return findVehicleSpecifications(manufacturer, model, modelYear, powertrain).find((item) => (
    normalize(item.powertrainDetail) === normalizedDetail
    && item.trims.some((candidate) => normalize(candidate) === normalizedTrim)
  ));
}
