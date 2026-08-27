import type { OfficialManualSiteId, VehicleProfile } from "../types";

export interface ManualBrandSource {
  manufacturer: string;
  label: string;
  siteId: OfficialManualSiteId;
  baseUrl: string;
  homeUrl: string;
}

export interface VehicleManualSource extends ManualBrandSource {
  model: string;
  modelYear: number;
  projectCode: string;
  manualUrl: string;
  imageUrl: string;
}

export const BMW_DRIVER_GUIDE = {
  manufacturer: "BMW",
  label: "BMW",
  homeUrl: "https://www.bmw.co.kr/ko/topics/owners/online-manual/bmw-driver-guide.html",
} as const;

export const MANUAL_BRANDS: ManualBrandSource[] = [
  {
    manufacturer: "현대",
    label: "현대자동차",
    siteId: "hmc",
    baseUrl: "https://ownersmanual.hyundai.com",
    homeUrl: "https://ownersmanual.hyundai.com/main?langCode=ko_KR&countryCode=A99",
  },
  {
    manufacturer: "기아",
    label: "기아",
    siteId: "kia",
    baseUrl: "https://ownersmanual.kia.com",
    homeUrl: "https://ownersmanual.kia.com/main?langCode=ko_KR&countryCode=A99",
  },
  {
    manufacturer: "제네시스",
    label: "제네시스",
    siteId: "genesis",
    baseUrl: "https://ownersmanual.genesis.com",
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
    imageUrl: "https://ownersmanual.hyundai.com/api/v2/hmc/files/6406/H_FE_2024.png",
  },
  {
    ...MANUAL_BRANDS[2],
    model: "ELECTRIFIED GV70",
    modelYear: 2027,
    projectCode: "JKEV",
    manualUrl: "https://ownersmanual.genesis.com/manual/ELECTRIFIED%20GV70?projCode=JKEV&year=2027&langCode=ko_KR&countryCode=A99",
    imageUrl: "https://ownersmanual.genesis.com/api/v2/genesis/files/6295/JK1EV-CeresBlue-MSA-01-18F-630x240.png",
  },
];

function normalize(value: string): string {
  return value.trim().toLocaleUpperCase("ko-KR").replace(/\s+/g, " ");
}

export function getManualBrand(manufacturer: string): ManualBrandSource | undefined {
  const target = normalize(manufacturer);
  return MANUAL_BRANDS.find((brand) => normalize(brand.manufacturer) === target);
}

export function getManualBrandBySiteId(siteId: OfficialManualSiteId): ManualBrandSource | undefined {
  return MANUAL_BRANDS.find((brand) => brand.siteId === siteId);
}

export function buildManualUrl(brand: ManualBrandSource, modelName: string, projectCode: string, modelYear: number): string {
  const modelPath = encodeURIComponent(modelName).replace(/%20/g, "%20");
  return `${brand.baseUrl}/manual/${modelPath}?projCode=${encodeURIComponent(projectCode)}&year=${modelYear}&langCode=ko_KR&countryCode=A99`;
}

export function getVehicleManual(vehicle: VehicleProfile): VehicleManualSource | undefined {
  const manufacturer = normalize(vehicle.manufacturer);
  const model = normalize(vehicle.model);
  const metadata = vehicle.manual;
  if (metadata && metadata.modelYear === vehicle.modelYear && normalize(metadata.modelName) === model) {
    const brand = getManualBrandBySiteId(metadata.siteId);
    if (brand && normalize(brand.manufacturer) === manufacturer) {
      return {
        ...brand,
        model: metadata.modelName,
        modelYear: metadata.modelYear,
        projectCode: metadata.projectCode,
        manualUrl: buildManualUrl(brand, metadata.modelName, metadata.projectCode, metadata.modelYear),
        imageUrl: metadata.imageUrl,
      };
    }
  }
  return VEHICLE_MANUALS.find((source) => (
    normalize(source.manufacturer) === manufacturer
    && normalize(source.model) === model
    && source.modelYear === vehicle.modelYear
  ));
}
