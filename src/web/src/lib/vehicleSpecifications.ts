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
  powertrainDetailAliases?: string[];
  /** 비어 있으면 용량과 무관한 실제 트림명을 사용자가 입력한다. */
  trims: string[];
  trimAliases?: string[];
  batteryCapacityKwh?: number;
  fuelTankCapacityLiters?: number;
  sourceUrl: string;
  verifiedAt: string;
}

interface EnergyStorageDefinition {
  batteryCapacityKwh?: number;
  fuelTankCapacityLiters?: number;
  sourceUrl: string;
  verifiedAt: string;
}

interface ModelDefinition {
  id: string;
  manufacturer: string;
  manufacturerAliases: string[];
  model: string;
  modelAliases: string[];
  modelYears: number[];
  powertrain?: Powertrain;
  sourceUrl?: string;
  verifiedAt?: string;
  variants: Array<{
    id: string;
    powertrainDetail: string;
    powertrainDetailAliases?: string[];
    trims?: string[];
    trimAliases?: string[];
    energyStorageId: string;
  }>;
}

const HYUNDAI_EV_SOURCE = "https://www.hyundai.com/kr/ko/service-membership/ev/ev-battery-cell-information";
const KIA_EV_SOURCE = "https://www.kia.com/content/dam/kwp/kr/ko/vehicles/pdf/etc/kia-consulting-guide_battery.pdf";
const KIA_EV3_SOURCE = "https://www.kia.com/kr/vehicles/ev3/specification";
const KIA_EV4_SOURCE = "https://www.kia.com/kr/vehicles/ev4/specification";
const KIA_EV4_GT_SOURCE = "https://www.kia.com/kr/vehicles/ev4-gt/specification";
const KIA_EV5_SOURCE = "https://www.kia.com/kr/vehicles/ev5/specification";
const KIA_EV5_GT_SOURCE = "https://www.kia.com/kr/vehicles/ev5-gt/specification";
const KIA_EV6_SOURCE = "https://www.kia.com/kr/vehicles/ev6/specification";
const KIA_EV6_GT_SOURCE = "https://www.kia.com/kr/vehicles/ev6-gt/specification";
const KIA_EV9_SOURCE = "https://www.kia.com/kr/vehicles/ev9/specification";
const KIA_EV9_GT_SOURCE = "https://www.kia.com/kr/vehicles/ev9-gt/specification";
const KIA_RAY_EV_SOURCE = "https://www.kia.com/kr/vehicles/ray-ev/specification";
const KIA_NIRO_PLUS_SOURCE = "https://www.kia.com/kr/vehicles/niro-plus/price";
const KIA_K5_GASOLINE_2025_SOURCE = "https://ownersmanual.kia.com/full_webhelp/DL3/2025/ko_KR/topics/chapter9_5.html";
const KIA_K5_GASOLINE_2026_SOURCE = "https://ownersmanual.kia.com/full_webhelp/DL3/2026/ko_KR/topics/chapter9_5.html";
const KIA_K5_HYBRID_2025_SOURCE = "https://ownersmanual.kia.com/full_webhelp/DL3KH/2025/ko_KR/topics/chapter9_5.html";
const KIA_K5_HYBRID_2026_SOURCE = "https://ownersmanual.kia.com/full_webhelp/DL3KH/2026/ko_KR/topics/chapter9_5.html";
const GENESIS_EV_SOURCE = "https://www.genesis.com/kr/ko/support/notice/detail/0000000547.html";

/** 용량·공식 근거는 한 번만 저장하고 여러 차종/연식/구동 조합에서 참조한다. */
export const ENERGY_STORAGE_DEFINITIONS: Record<string, EnergyStorageDefinition> = {
  "hyundai-48.6": { batteryCapacityKwh: 48.6, sourceUrl: HYUNDAI_EV_SOURCE, verifiedAt: "2026-09-03" },
  "hyundai-42": { batteryCapacityKwh: 42, sourceUrl: HYUNDAI_EV_SOURCE, verifiedAt: "2026-09-03" },
  "hyundai-49": { batteryCapacityKwh: 49, sourceUrl: HYUNDAI_EV_SOURCE, verifiedAt: "2026-09-03" },
  "hyundai-53": { batteryCapacityKwh: 53, sourceUrl: HYUNDAI_EV_SOURCE, verifiedAt: "2026-09-03" },
  "hyundai-63": { batteryCapacityKwh: 63, sourceUrl: HYUNDAI_EV_SOURCE, verifiedAt: "2026-09-03" },
  "hyundai-64.8": { batteryCapacityKwh: 64.8, sourceUrl: HYUNDAI_EV_SOURCE, verifiedAt: "2026-09-03" },
  "hyundai-77.4": { batteryCapacityKwh: 77.4, sourceUrl: HYUNDAI_EV_SOURCE, verifiedAt: "2026-09-03" },
  "hyundai-84": { batteryCapacityKwh: 84, sourceUrl: HYUNDAI_EV_SOURCE, verifiedAt: "2026-09-03" },
  "hyundai-110.3": { batteryCapacityKwh: 110.3, sourceUrl: HYUNDAI_EV_SOURCE, verifiedAt: "2026-09-03" },
  "kia-58.3": { batteryCapacityKwh: 58.3, sourceUrl: KIA_EV3_SOURCE, verifiedAt: "2026-09-03" },
  "kia-35.2": { batteryCapacityKwh: 35.2, sourceUrl: KIA_RAY_EV_SOURCE, verifiedAt: "2026-09-03" },
  "kia-60.3": { batteryCapacityKwh: 60.3, sourceUrl: KIA_EV5_SOURCE, verifiedAt: "2026-09-03" },
  "kia-62.9": { batteryCapacityKwh: 62.9, sourceUrl: KIA_EV6_SOURCE, verifiedAt: "2026-09-03" },
  "kia-64": { batteryCapacityKwh: 64, sourceUrl: KIA_NIRO_PLUS_SOURCE, verifiedAt: "2026-09-03" },
  "kia-64.8": { batteryCapacityKwh: 64.8, sourceUrl: KIA_EV_SOURCE, verifiedAt: "2026-09-03" },
  "kia-76.1": { batteryCapacityKwh: 76.1, sourceUrl: KIA_EV9_SOURCE, verifiedAt: "2026-09-03" },
  "kia-81.4": { batteryCapacityKwh: 81.4, sourceUrl: KIA_EV_SOURCE, verifiedAt: "2026-09-03" },
  "kia-84": { batteryCapacityKwh: 84, sourceUrl: KIA_EV6_SOURCE, verifiedAt: "2026-09-03" },
  "kia-99.8": { batteryCapacityKwh: 99.8, sourceUrl: KIA_EV9_SOURCE, verifiedAt: "2026-09-03" },
  "kia-fuel-50": { fuelTankCapacityLiters: 50, sourceUrl: KIA_K5_HYBRID_2026_SOURCE, verifiedAt: "2026-09-04" },
  "kia-fuel-60": { fuelTankCapacityLiters: 60, sourceUrl: KIA_K5_GASOLINE_2026_SOURCE, verifiedAt: "2026-09-04" },
  "genesis-84": { batteryCapacityKwh: 84, sourceUrl: GENESIS_EV_SOURCE, verifiedAt: "2026-09-03" },
  "genesis-94.5": { batteryCapacityKwh: 94.5, sourceUrl: GENESIS_EV_SOURCE, verifiedAt: "2026-09-03" },
};

const HYUNDAI = { manufacturer: "현대", manufacturerAliases: ["현대", "현대자동차", "HYUNDAI"] };
const KIA = { manufacturer: "기아", manufacturerAliases: ["기아", "KIA"] };
const GENESIS = { manufacturer: "제네시스", manufacturerAliases: ["제네시스", "GENESIS"] };
const standardLongRange = (standardStorageId: string, longRangeStorageId: string, includeAwd = false) => [
  { id: "standard-2wd", powertrainDetail: "스탠다드 2WD", energyStorageId: standardStorageId },
  { id: "long-range-2wd", powertrainDetail: "롱레인지 2WD", energyStorageId: longRangeStorageId },
  ...(includeAwd ? [{ id: "long-range-awd", powertrainDetail: "롱레인지 AWD", powertrainDetailAliases: ["롱레인지 4WD"], energyStorageId: longRangeStorageId }] : []),
];

const MODELS: ModelDefinition[] = [
  { id: "hyundai-ioniq5", ...HYUNDAI, model: "아이오닉 5", modelAliases: ["아이오닉 5", "아이오닉5", "IONIQ 5", "더 뉴 아이오닉 5"], modelYears: [2025, 2026, 2027], variants: standardLongRange("hyundai-63", "hyundai-84", true) },
  { id: "hyundai-ioniq5-n", ...HYUNDAI, model: "아이오닉 5 N", modelAliases: ["아이오닉 5 N", "아이오닉5N", "IONIQ 5 N"], modelYears: [2024, 2025, 2026, 2027], variants: [{ id: "n-awd", powertrainDetail: "N AWD", powertrainDetailAliases: ["AWD", "듀얼 모터 AWD"], energyStorageId: "hyundai-84" }] },
  { id: "hyundai-ioniq6", ...HYUNDAI, model: "아이오닉 6", modelAliases: ["아이오닉 6", "아이오닉6", "IONIQ 6"], modelYears: [2023, 2024, 2025], variants: standardLongRange("hyundai-53", "hyundai-77.4", true) },
  { id: "hyundai-new-ioniq6", ...HYUNDAI, model: "아이오닉 6", modelAliases: ["아이오닉 6", "아이오닉6", "IONIQ 6", "더 뉴 아이오닉 6"], modelYears: [2026, 2027], variants: standardLongRange("hyundai-63", "hyundai-84", true) },
  { id: "hyundai-ioniq6-n", ...HYUNDAI, model: "아이오닉 6 N", modelAliases: ["아이오닉 6 N", "아이오닉6N", "IONIQ 6 N"], modelYears: [2026, 2027], variants: [{ id: "n-awd", powertrainDetail: "N AWD", powertrainDetailAliases: ["AWD", "듀얼 모터 AWD"], energyStorageId: "hyundai-84" }] },
  { id: "hyundai-ioniq9", ...HYUNDAI, model: "아이오닉 9", modelAliases: ["아이오닉 9", "아이오닉9", "IONIQ 9"], modelYears: [2026, 2027], variants: [
    { id: "range-2wd", powertrainDetail: "항속형 2WD", energyStorageId: "hyundai-110.3" },
    { id: "range-awd", powertrainDetail: "항속형 AWD", powertrainDetailAliases: ["항속형 4WD"], energyStorageId: "hyundai-110.3" },
    { id: "performance-awd", powertrainDetail: "성능형 AWD", powertrainDetailAliases: ["성능형 4WD"], energyStorageId: "hyundai-110.3" },
  ] },
  { id: "hyundai-kona-electric", ...HYUNDAI, model: "코나 Electric", modelAliases: ["코나 ELECTRIC", "코나 일렉트릭", "코나EV", "코나 EV", "디 올 뉴 코나", "THE ALL NEW KONA ELECTRIC"], modelYears: [2024, 2025, 2026], variants: standardLongRange("hyundai-48.6", "hyundai-64.8") },
  { id: "hyundai-casper-electric", ...HYUNDAI, model: "캐스퍼 일렉트릭", modelAliases: ["캐스퍼 일렉트릭", "캐스퍼 ELECTRIC", "캐스퍼 EV"], modelYears: [2025, 2026, 2027], variants: [
    { id: "base-2wd", powertrainDetail: "기본형 2WD", powertrainDetailAliases: ["기본형"], energyStorageId: "hyundai-42" },
    { id: "range-2wd", powertrainDetail: "항속형 2WD", powertrainDetailAliases: ["항속형"], energyStorageId: "hyundai-49" },
    { id: "cross-2wd", powertrainDetail: "크로스 2WD", powertrainDetailAliases: ["크로스"], energyStorageId: "hyundai-49" },
  ] },
  { id: "kia-ev3", ...KIA, model: "EV3", modelAliases: ["EV3"], modelYears: [2025, 2026, 2027], sourceUrl: KIA_EV3_SOURCE, variants: [
    ...standardLongRange("kia-58.3", "kia-81.4"),
    { id: "long-range-4wd", powertrainDetail: "롱레인지 4WD", powertrainDetailAliases: ["롱레인지 AWD"], energyStorageId: "kia-81.4" },
  ] },
  { id: "kia-ev4", ...KIA, model: "EV4", modelAliases: ["EV4"], modelYears: [2026, 2027], sourceUrl: KIA_EV4_SOURCE, variants: [
    { id: "standard-2wd", powertrainDetail: "스탠다드 2WD", energyStorageId: "kia-58.3" },
    { id: "standard-4wd", powertrainDetail: "스탠다드 4WD", powertrainDetailAliases: ["스탠다드 AWD"], energyStorageId: "kia-58.3" },
    { id: "long-range-2wd", powertrainDetail: "롱레인지 2WD", energyStorageId: "kia-81.4" },
    { id: "long-range-4wd", powertrainDetail: "롱레인지 4WD", powertrainDetailAliases: ["롱레인지 AWD"], energyStorageId: "kia-81.4" },
  ] },
  { id: "kia-ev5", ...KIA, model: "EV5", modelAliases: ["EV5"], modelYears: [2026, 2027], sourceUrl: KIA_EV5_SOURCE, variants: [
    { id: "standard-2wd", powertrainDetail: "스탠다드 2WD", energyStorageId: "kia-60.3" },
    { id: "long-range-2wd", powertrainDetail: "롱레인지 2WD", energyStorageId: "kia-81.4" },
    { id: "long-range-4wd", powertrainDetail: "롱레인지 4WD", powertrainDetailAliases: ["롱레인지 AWD"], energyStorageId: "kia-81.4" },
  ] },
  { id: "kia-ev6", ...KIA, model: "EV6", modelAliases: ["EV6", "더 뉴 EV6"], modelYears: [2025, 2026, 2027], sourceUrl: KIA_EV6_SOURCE, variants: [
    { id: "standard-2wd", powertrainDetail: "스탠다드 2WD", trims: ["라이트", "에어", "어스"], energyStorageId: "kia-62.9" },
    { id: "long-range-2wd", powertrainDetail: "롱레인지 2WD", trims: ["라이트", "에어", "어스", "GT-Line"], energyStorageId: "kia-84" },
    { id: "long-range-4wd", powertrainDetail: "롱레인지 4WD", powertrainDetailAliases: ["롱레인지 AWD"], trims: ["라이트", "에어", "어스", "GT-Line"], energyStorageId: "kia-84" },
  ] },
  { id: "kia-ev3-gt", ...KIA, model: "EV3 GT", modelAliases: ["EV3 GT"], modelYears: [2026, 2027], sourceUrl: "https://www.kia.com/kr/vehicles/ev3-gt/specification", variants: [{ id: "gt-4wd", powertrainDetail: "GT 4WD", powertrainDetailAliases: ["GT AWD", "4WD (GT)"], energyStorageId: "kia-81.4" }] },
  { id: "kia-ev4-gt", ...KIA, model: "EV4 GT", modelAliases: ["EV4 GT"], modelYears: [2026, 2027], sourceUrl: KIA_EV4_GT_SOURCE, variants: [{ id: "gt-4wd", powertrainDetail: "GT 4WD", powertrainDetailAliases: ["GT AWD", "4WD (GT)"], energyStorageId: "kia-81.4" }] },
  { id: "kia-ev5-gt", ...KIA, model: "EV5 GT", modelAliases: ["EV5 GT"], modelYears: [2026, 2027], sourceUrl: KIA_EV5_GT_SOURCE, variants: [{ id: "gt-4wd", powertrainDetail: "GT 4WD", powertrainDetailAliases: ["GT AWD", "4WD (GT)"], energyStorageId: "kia-81.4" }] },
  { id: "kia-ev6-gt", ...KIA, model: "EV6 GT", modelAliases: ["EV6 GT", "더 뉴 EV6 GT"], modelYears: [2025, 2026, 2027], sourceUrl: KIA_EV6_GT_SOURCE, variants: [{ id: "gt-4wd", powertrainDetail: "GT 4WD", powertrainDetailAliases: ["GT AWD", "4WD (GT)"], energyStorageId: "kia-84" }] },
  { id: "kia-ev9-gt", ...KIA, model: "EV9 GT", modelAliases: ["EV9 GT"], modelYears: [2026, 2027], sourceUrl: KIA_EV9_GT_SOURCE, variants: [{ id: "gt-4wd", powertrainDetail: "GT 4WD", powertrainDetailAliases: ["GT AWD", "4WD (GT)"], energyStorageId: "kia-99.8" }] },
  { id: "kia-ev9", ...KIA, model: "EV9", modelAliases: ["EV9", "더 기아 EV9"], modelYears: [2024, 2025, 2026, 2027], sourceUrl: KIA_EV9_SOURCE, variants: [
    { id: "standard-2wd", powertrainDetail: "스탠다드 2WD", energyStorageId: "kia-76.1" },
    { id: "long-range-2wd", powertrainDetail: "롱레인지 2WD", energyStorageId: "kia-99.8" },
    { id: "long-range-4wd", powertrainDetail: "롱레인지 4WD", powertrainDetailAliases: ["롱레인지 AWD"], energyStorageId: "kia-99.8" },
  ] },
  { id: "kia-niro-ev", ...KIA, model: "니로 EV", modelAliases: ["니로 EV", "니로EV", "NIRO EV"], modelYears: [2023, 2024, 2025, 2026], variants: [{ id: "2wd", powertrainDetail: "2WD", energyStorageId: "kia-64.8" }] },
  { id: "kia-niro-plus", ...KIA, model: "니로 플러스", modelAliases: ["니로 플러스", "니로PLUS", "NIRO PLUS"], modelYears: [2023], variants: [{ id: "2wd", powertrainDetail: "2WD", energyStorageId: "kia-64" }] },
  { id: "kia-ray-ev", ...KIA, model: "레이 EV", modelAliases: ["레이 EV", "레이EV", "RAY EV"], modelYears: [2024, 2025, 2026, 2027], sourceUrl: KIA_RAY_EV_SOURCE, variants: [{ id: "2wd", powertrainDetail: "2WD", powertrainDetailAliases: ["EV 2WD"], energyStorageId: "kia-35.2" }] },
  { id: "kia-k5-gasoline", ...KIA, model: "K5", modelAliases: ["K5", "더 뉴 K5"], modelYears: [2025], powertrain: "gasoline", sourceUrl: KIA_K5_GASOLINE_2025_SOURCE, verifiedAt: "2026-09-04", variants: [
    { id: "1.6-t-gdi", powertrainDetail: "스마트스트림 G1.6 T-GDI", powertrainDetailAliases: ["1.6 가솔린 터보", "1.6 터보", "G1.6 T-GDI"], energyStorageId: "kia-fuel-60" },
    { id: "2.0-cvvl", powertrainDetail: "스마트스트림 G2.0 CVVL", powertrainDetailAliases: ["2.0 가솔린", "2.0", "G2.0 CVVL"], energyStorageId: "kia-fuel-60" },
  ] },
  { id: "kia-k5-gasoline", ...KIA, model: "K5", modelAliases: ["K5", "더 뉴 K5"], modelYears: [2026], powertrain: "gasoline", sourceUrl: KIA_K5_GASOLINE_2026_SOURCE, verifiedAt: "2026-09-04", variants: [
    { id: "1.6-t-gdi", powertrainDetail: "스마트스트림 G1.6 T-GDI", powertrainDetailAliases: ["1.6 가솔린 터보", "1.6 터보", "G1.6 T-GDI"], energyStorageId: "kia-fuel-60" },
    { id: "2.0-cvvl", powertrainDetail: "스마트스트림 G2.0 CVVL", powertrainDetailAliases: ["2.0 가솔린", "2.0", "G2.0 CVVL"], energyStorageId: "kia-fuel-60" },
  ] },
  { id: "kia-k5-hybrid", ...KIA, model: "K5", modelAliases: ["K5", "더 뉴 K5", "K5 하이브리드"], modelYears: [2025], powertrain: "hybrid", sourceUrl: KIA_K5_HYBRID_2025_SOURCE, verifiedAt: "2026-09-04", variants: [
    { id: "2.0-hybrid", powertrainDetail: "스마트스트림 G2.0 하이브리드", powertrainDetailAliases: ["2.0 하이브리드", "하이브리드"], energyStorageId: "kia-fuel-50" },
  ] },
  { id: "kia-k5-hybrid", ...KIA, model: "K5", modelAliases: ["K5", "더 뉴 K5", "K5 하이브리드"], modelYears: [2026], powertrain: "hybrid", sourceUrl: KIA_K5_HYBRID_2026_SOURCE, verifiedAt: "2026-09-04", variants: [
    { id: "2.0-hybrid", powertrainDetail: "스마트스트림 G2.0 하이브리드", powertrainDetailAliases: ["2.0 하이브리드", "하이브리드"], energyStorageId: "kia-fuel-50" },
  ] },
  { id: "genesis-gv60", ...GENESIS, model: "GV60", modelAliases: ["GV60"], modelYears: [2026, 2027], variants: [
    { id: "standard-2wd", powertrainDetail: "스탠다드 2WD", energyStorageId: "genesis-84" },
    { id: "standard-awd", powertrainDetail: "스탠다드 AWD", powertrainDetailAliases: ["스탠다드 4WD"], energyStorageId: "genesis-84" },
    { id: "performance-awd", powertrainDetail: "퍼포먼스 AWD", powertrainDetailAliases: ["퍼포먼스 4WD"], energyStorageId: "genesis-84" },
  ] },
  { id: "genesis-gv60-magma", ...GENESIS, model: "GV60 MAGMA", modelAliases: ["GV60 MAGMA", "GV60 마그마"], modelYears: [2027], variants: [{ id: "magma-awd", powertrainDetail: "마그마 AWD", powertrainDetailAliases: ["AWD"], energyStorageId: "genesis-84" }] },
  { id: "genesis-electrified-gv70", ...GENESIS, model: "ELECTRIFIED GV70", modelAliases: ["ELECTRIFIED GV70", "GV70 전동화", "일렉트리파이드 GV70", "EGV70"], modelYears: [2026, 2027], variants: [{ id: "awd", powertrainDetail: "듀얼 모터 AWD", powertrainDetailAliases: ["AWD (듀얼 모터)", "듀얼모터 AWD"], trims: ["기본 모델"], trimAliases: ["기본형"], energyStorageId: "genesis-84" }] },
  { id: "genesis-electrified-g80", ...GENESIS, model: "ELECTRIFIED G80", modelAliases: ["ELECTRIFIED G80", "G80 전동화", "일렉트리파이드 G80", "EG80"], modelYears: [2025, 2026, 2027], variants: [{ id: "dual-awd", powertrainDetail: "듀얼 모터 AWD", powertrainDetailAliases: ["AWD", "듀얼모터 AWD"], energyStorageId: "genesis-94.5" }] },
];

export const VEHICLE_SPECIFICATIONS: VehicleSpecification[] = MODELS.flatMap((definition) => definition.modelYears.flatMap((modelYear) => definition.variants.map((variant) => {
  const storage = ENERGY_STORAGE_DEFINITIONS[variant.energyStorageId];
  if (!storage) throw new Error(`Unknown energy storage definition: ${variant.energyStorageId}`);
  return {
    id: `${definition.id}-${modelYear}-${variant.id}`,
    manufacturer: definition.manufacturer,
    manufacturerAliases: definition.manufacturerAliases,
    model: definition.model,
    modelAliases: definition.modelAliases,
    modelYear,
    powertrain: definition.powertrain ?? "electric",
    powertrainDetail: variant.powertrainDetail,
    powertrainDetailAliases: variant.powertrainDetailAliases,
    trims: variant.trims ?? [],
    trimAliases: variant.trimAliases,
    ...storage,
    ...(definition.sourceUrl ? { sourceUrl: definition.sourceUrl } : {}),
    ...(definition.verifiedAt ? { verifiedAt: definition.verifiedAt } : {}),
  };
})));

function normalize(value: string): string {
  return value.toLocaleUpperCase("ko-KR").replace(/[^0-9A-Z가-힣]/g, "");
}

export function findVehicleSpecifications(manufacturer: string, model: string, modelYear: number, powertrain: Powertrain): VehicleSpecification[] {
  const normalizedManufacturer = normalize(manufacturer);
  const normalizedModel = normalize(model);
  if (!normalizedManufacturer || !normalizedModel || !Number.isInteger(modelYear)) return [];
  return VEHICLE_SPECIFICATIONS.filter((item) => item.modelYear === modelYear
    && item.powertrain === powertrain
    && item.manufacturerAliases.some((alias) => normalize(alias) === normalizedManufacturer)
    && item.modelAliases.some((alias) => normalize(alias) === normalizedModel));
}

export function resolveVehicleEnergySpecification(manufacturer: string, model: string, modelYear: number, powertrain: Powertrain, powertrainDetail: string): VehicleSpecification | undefined {
  const normalizedDetail = normalize(powertrainDetail);
  return findVehicleSpecifications(manufacturer, model, modelYear, powertrain).find((item) => [item.powertrainDetail, ...(item.powertrainDetailAliases ?? [])]
    .some((candidate) => normalize(candidate) === normalizedDetail));
}

export function resolveVehicleSpecification(manufacturer: string, model: string, modelYear: number, powertrain: Powertrain, powertrainDetail: string, trim: string): VehicleSpecification | undefined {
  const specification = resolveVehicleEnergySpecification(manufacturer, model, modelYear, powertrain, powertrainDetail);
  if (!specification || !normalize(trim)) return undefined;
  if (specification.trims.length === 0) return specification;
  const normalizedTrim = normalize(trim);
  return [...specification.trims, ...(specification.trimAliases ?? [])]
    .some((candidate) => normalize(candidate) === normalizedTrim) ? specification : undefined;
}
