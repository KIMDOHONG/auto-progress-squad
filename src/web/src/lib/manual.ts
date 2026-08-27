import type { VehicleProfile } from "../types";

export interface ManualBrandSource {
  manufacturer: string;
  label: string;
  homeUrl: string;
}

export interface VehicleManualSource extends ManualBrandSource {
  model: string;
  modelYear: number;
  projectCode: string;
  manualUrl: string;
}

export const MANUAL_BRANDS: ManualBrandSource[] = [
  {
    manufacturer: "현대",
    label: "현대자동차",
    homeUrl: "https://ownersmanual.hyundai.com/main?langCode=ko_KR&countryCode=A99",
  },
  {
    manufacturer: "기아",
    label: "기아",
    homeUrl: "https://ownersmanual.kia.com/main?langCode=ko_KR&countryCode=A99",
  },
  {
    manufacturer: "제네시스",
    label: "제네시스",
    homeUrl: "https://ownersmanual.genesis.com/main?langCode=ko_KR&countryCode=A99",
  },
];

const VEHICLE_MANUALS: VehicleManualSource[] = [
  {
    ...MANUAL_BRANDS[0],
    model: "넥쏘",
    modelYear: 2021,
    projectCode: "FE",
    manualUrl: "https://ownersmanual.hyundai.com/manual/%EB%84%A5%EC%8F%98?projCode=FE&year=2021&langCode=ko_KR&countryCode=A99",
  },
  {
    ...MANUAL_BRANDS[2],
    model: "ELECTRIFIED GV70",
    modelYear: 2027,
    projectCode: "JKEV",
    manualUrl: "https://ownersmanual.genesis.com/manual/ELECTRIFIED%20GV70?projCode=JKEV&year=2027&langCode=ko_KR&countryCode=A99",
  },
];

function normalize(value: string): string {
  return value.trim().toLocaleUpperCase("ko-KR").replace(/\s+/g, " ");
}

export function getManualBrand(manufacturer: string): ManualBrandSource | undefined {
  const target = normalize(manufacturer);
  return MANUAL_BRANDS.find((brand) => normalize(brand.manufacturer) === target);
}

export function getVehicleManual(vehicle: VehicleProfile): VehicleManualSource | undefined {
  const manufacturer = normalize(vehicle.manufacturer);
  const model = normalize(vehicle.model);
  return VEHICLE_MANUALS.find((source) => (
    normalize(source.manufacturer) === manufacturer
    && normalize(source.model) === model
    && source.modelYear === vehicle.modelYear
  ));
}
