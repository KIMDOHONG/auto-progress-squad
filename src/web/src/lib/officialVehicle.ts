import { getManualBrandBySiteId, MANUAL_BRANDS, buildManualUrl, type ManualBrandSource } from "./manual";
import type { OfficialManualMetadata, OfficialManualSiteId, Powertrain } from "../types";

interface CatalogModel {
  langModelName: string;
}

interface DetailModel {
  modelName: string;
  projCode: string;
  year: string;
  fuel: string;
  mainImgUrl: string;
}

interface DetailResponse {
  years: string[];
  yearModels: Record<string, DetailModel[]>;
}

export interface ParsedVehicleRequest {
  manufacturer?: string;
  manufacturerSupport: "connected" | "official-link" | "unsupported" | "unspecified";
  manufacturerManualUrl?: string;
  modelQuery: string;
  modelYear: number;
}

export interface OfficialVehicleCandidate {
  id: string;
  manufacturer: string;
  label: string;
  siteId: OfficialManualSiteId;
  modelName: string;
  projectCode: string;
  modelYear: number;
  fuel: string;
  suggestedPowertrain: Powertrain;
  imageUrl: string;
  manualUrl: string;
}

export interface OfficialVehicleSearchResult {
  candidates: OfficialVehicleCandidate[];
  correctedModelName?: string;
  availableYears?: number[];
}

const REQUEST_TIMEOUT_MS = 8_000;
const catalogCache = new Map<OfficialManualSiteId, Promise<CatalogModel[]>>();
const detailCache = new Map<string, Promise<DetailResponse>>();
const REGISTRATION_WORDS = /(자동차|차량|내\s*차|프로필|등록|추가|저장|해\s*줘|해주세요|해줘|시켜줘|부탁해|입니다|이에요|예요)/gi;
const BRAND_ALIASES: Array<{
  pattern: RegExp;
  manufacturer: string;
  support: ParsedVehicleRequest["manufacturerSupport"];
  manualUrl?: string;
}> = [
  { pattern: /(현대자동차|현대|hyundai|현다이)/i, manufacturer: "현대", support: "connected" },
  { pattern: /(기아자동차|기아|kia)/i, manufacturer: "기아", support: "connected" },
  { pattern: /(제네시스|genesis)/i, manufacturer: "제네시스", support: "connected" },
  { pattern: /(쉐보레|chevrolet|GM대우)/i, manufacturer: "쉐보레", support: "official-link", manualUrl: "https://www.chevrolet.co.kr/owner-manuals" },
  { pattern: /(KG\s*모빌리티|KGM|쌍용자동차|쌍용)/i, manufacturer: "KGM", support: "official-link", manualUrl: "https://www.kg-mobility.com/sr/update-download/download-center/instruction-manual" },
  { pattern: /(BMW|비엠더블유|비엠)/i, manufacturer: "BMW", support: "unsupported" },
  { pattern: /(메르세데스\s*벤츠|벤츠|mercedes(?:-benz)?)/i, manufacturer: "메르세데스-벤츠", support: "unsupported" },
  { pattern: /(아우디|audi)/i, manufacturer: "아우디", support: "unsupported" },
  { pattern: /(폭스바겐|volkswagen)/i, manufacturer: "폭스바겐", support: "unsupported" },
  { pattern: /(볼보|volvo)/i, manufacturer: "볼보", support: "unsupported" },
  { pattern: /(테슬라|tesla)/i, manufacturer: "테슬라", support: "unsupported" },
  { pattern: /(토요타|도요타|toyota)/i, manufacturer: "토요타", support: "unsupported" },
  { pattern: /(렉서스|lexus)/i, manufacturer: "렉서스", support: "unsupported" },
  { pattern: /(혼다|honda)/i, manufacturer: "혼다", support: "unsupported" },
  { pattern: /(닛산|nissan)/i, manufacturer: "닛산", support: "unsupported" },
  { pattern: /(르노코리아|르노삼성|르노|renault)/i, manufacturer: "르노코리아", support: "unsupported" },
  { pattern: /(포드|ford)/i, manufacturer: "포드", support: "unsupported" },
  { pattern: /(지프|jeep)/i, manufacturer: "지프", support: "unsupported" },
  { pattern: /(포르쉐|porsche)/i, manufacturer: "포르쉐", support: "unsupported" },
];
const MODEL_ALIASES: Record<string, string> = {
  EGV70: "ELECTRIFIED GV70",
  전기GV70: "ELECTRIFIED GV70",
  일렉트리파이드GV70: "ELECTRIFIED GV70",
  아이오닉5엔: "아이오닉 5 N",
  아이오닉오N: "아이오닉 5 N",
};

function normalize(value: string): string {
  return value.toLocaleUpperCase("ko-KR").replace(/[^0-9A-Z가-힣]/g, "");
}

function officialBrands(manufacturer?: string): ManualBrandSource[] {
  if (!manufacturer) return MANUAL_BRANDS;
  return MANUAL_BRANDS.filter((brand) => normalize(brand.manufacturer) === normalize(manufacturer));
}

async function fetchJson<T>(url: string): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url, { signal: controller.signal, headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`official_manual_http_${response.status}`);
    return await response.json() as T;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function flattenCatalog(payload: Record<string, CatalogModel[]>): CatalogModel[] {
  const unique = new Map<string, CatalogModel>();
  for (const models of Object.values(payload)) {
    for (const model of models) unique.set(normalize(model.langModelName), model);
  }
  return [...unique.values()];
}

function fetchCatalog(brand: ManualBrandSource): Promise<CatalogModel[]> {
  const cached = catalogCache.get(brand.siteId);
  if (cached) return cached;
  const request = fetchJson<Record<string, CatalogModel[]>>(
    `${brand.baseUrl}/api/v2/${brand.siteId}/models?countryCode=A99&langCode=ko_KR`,
  ).then(flattenCatalog).catch((error) => {
    catalogCache.delete(brand.siteId);
    throw error;
  });
  catalogCache.set(brand.siteId, request);
  return request;
}

function fetchDetails(brand: ManualBrandSource, modelName: string): Promise<DetailResponse> {
  const key = `${brand.siteId}:${normalize(modelName)}`;
  const cached = detailCache.get(key);
  if (cached) return cached;
  const request = fetchJson<DetailResponse>(
    `${brand.baseUrl}/api/v3/${brand.siteId}/model?modelName=${encodeURIComponent(modelName)}&countryCode=A99&langCode=ko_KR`,
  ).catch((error) => {
    detailCache.delete(key);
    throw error;
  });
  detailCache.set(key, request);
  return request;
}

function levenshtein(left: string, right: string): number {
  if (!left.length) return right.length;
  if (!right.length) return left.length;
  const previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  for (let leftIndex = 1; leftIndex <= left.length; leftIndex += 1) {
    let diagonal = previous[0];
    previous[0] = leftIndex;
    for (let rightIndex = 1; rightIndex <= right.length; rightIndex += 1) {
      const above = previous[rightIndex];
      const cost = left[leftIndex - 1] === right[rightIndex - 1] ? 0 : 1;
      previous[rightIndex] = Math.min(previous[rightIndex] + 1, previous[rightIndex - 1] + 1, diagonal + cost);
      diagonal = above;
    }
  }
  return previous[right.length];
}

function similarity(query: string, candidate: string): number {
  const left = normalize(query);
  const right = normalize(candidate);
  if (left === right) return 1;
  if (right.includes(left) || left.includes(right)) return 0.88;
  return 1 - levenshtein(left, right) / Math.max(left.length, right.length, 1);
}

function inferPowertrain(fuel: string, modelName: string): Powertrain {
  const normalizedFuel = normalize(fuel);
  const normalizedModel = normalize(modelName);
  if (normalizedFuel.includes("FCEV")) return "hydrogen";
  if (normalizedFuel === "EV" || normalizedModel.includes("ELECTRIFIED")) return "electric";
  if (normalizedFuel.includes("HEV") || normalizedFuel.includes("PHEV") || normalizedModel.includes("HYBRID")) return "hybrid";
  if (normalizedFuel.includes("DIESEL")) return "diesel";
  return "gasoline";
}

function toCandidate(brand: ManualBrandSource, detail: DetailModel): OfficialVehicleCandidate {
  const imageUrl = new URL(detail.mainImgUrl, brand.baseUrl).toString();
  const modelYear = Number(detail.year);
  return {
    id: `${brand.siteId}-${detail.projCode}-${detail.year}`,
    manufacturer: brand.manufacturer,
    label: brand.label,
    siteId: brand.siteId,
    modelName: detail.modelName,
    projectCode: detail.projCode,
    modelYear,
    fuel: detail.fuel,
    suggestedPowertrain: inferPowertrain(detail.fuel, detail.modelName),
    imageUrl,
    manualUrl: buildManualUrl(brand, detail.modelName, detail.projCode, modelYear),
  };
}

export function parseVehicleRegistration(text: string): ParsedVehicleRequest | null {
  const yearMatch = text.match(/(?:19|20)\d{2}/);
  if (!yearMatch) return null;
  const modelYear = Number(yearMatch[0]);
  const brandMatch = BRAND_ALIASES.find(({ pattern }) => pattern.test(text));
  let modelQuery = text.replace(yearMatch[0], " ").replace(REGISTRATION_WORDS, " ");
  for (const alias of BRAND_ALIASES) modelQuery = modelQuery.replace(alias.pattern, " ");
  modelQuery = modelQuery.replace(/[,.!?()\[\]{}]/g, " ").replace(/\s+/g, " ").trim();
  const aliasModel = MODEL_ALIASES[normalize(modelQuery)];
  return modelQuery ? {
    manufacturer: brandMatch?.manufacturer,
    manufacturerSupport: brandMatch?.support ?? "unspecified",
    ...(brandMatch?.manualUrl ? { manufacturerManualUrl: brandMatch.manualUrl } : {}),
    modelQuery: aliasModel ?? modelQuery,
    modelYear,
  } : null;
}

export async function searchOfficialVehicles(request: ParsedVehicleRequest): Promise<OfficialVehicleSearchResult> {
  const brands = officialBrands(request.manufacturer);
  if (!brands.length) return { candidates: [] };

  const catalogs = await Promise.all(brands.map(async (brand) => ({ brand, models: await fetchCatalog(brand) })));
  const ranked = catalogs.flatMap(({ brand, models }) => models.map((model) => ({
    brand,
    model,
    score: similarity(request.modelQuery, model.langModelName),
  }))).sort((left, right) => right.score - left.score);

  const bestScore = ranked[0]?.score ?? 0;
  if (bestScore < 0.45) return { candidates: [] };
  const selectedModels = ranked.filter((entry) => entry.score >= Math.max(0.45, bestScore - 0.08)).slice(0, 4);
  const details = await Promise.all(selectedModels.map(async ({ brand, model, score }) => ({
    brand,
    model,
    score,
    response: await fetchDetails(brand, model.langModelName),
  })));
  const matchingCandidates = details.flatMap(({ brand, response }) => (
    response.yearModels[String(request.modelYear)] ?? []
  ).map((detail) => toCandidate(brand, detail)));

  const availableYears = [...new Set(details.flatMap(({ response }) => response.years.map(Number)))]
    .filter(Number.isFinite)
    .sort((left, right) => right - left);
  const correctedModelName = selectedModels[0] && normalize(selectedModels[0].model.langModelName) !== normalize(request.modelQuery)
    ? selectedModels[0].model.langModelName
    : undefined;
  return { candidates: matchingCandidates, correctedModelName, availableYears };
}

export function toManualMetadata(candidate: OfficialVehicleCandidate): OfficialManualMetadata {
  return {
    siteId: candidate.siteId,
    modelName: candidate.modelName,
    projectCode: candidate.projectCode,
    modelYear: candidate.modelYear,
    imageUrl: candidate.imageUrl,
    verifiedAt: new Date().toISOString(),
  };
}

export function getCandidateBrand(candidate: OfficialVehicleCandidate): ManualBrandSource | undefined {
  return getManualBrandBySiteId(candidate.siteId);
}
