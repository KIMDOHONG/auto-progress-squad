import type { VehicleProfile } from "../types";

export type RecallTargetResolution =
  | { kind: "active"; vehicle: VehicleProfile }
  | { kind: "explicit"; vehicle: VehicleProfile }
  | { kind: "ambiguous"; vehicles: VehicleProfile[] }
  | { kind: "missing"; query: string };

function compact(value: string): string {
  return value.toLocaleUpperCase("ko-KR").replace(/[^0-9A-Z가-힣]/g, "");
}

function identityTerms(vehicle: VehicleProfile): string[] {
  const year = String(vehicle.modelYear);
  const manufacturerModel = `${vehicle.manufacturer}${vehicle.model}`;
  return [
    vehicle.nickname,
    vehicle.model,
    manufacturerModel,
    `${vehicle.model}${year}`,
    `${year}${vehicle.model}`,
    `${manufacturerModel}${year}`,
    `${year}${manufacturerModel}`,
  ].map(compact).filter((value, index, values) => value.length >= 2 && values.indexOf(value) === index);
}

function remainingRecallSubject(text: string): string {
  let subject = compact(text);
  const genericTerms = [
    "자동차리콜센터", "리콜정보", "리콜조회", "리콜확인", "리콜",
    "현재활성차량", "활성차량", "현재차량", "선택차량", "내차량", "내자동차", "내차",
    "조회해주세요", "조회해줘", "확인해주세요", "확인해줘", "알려주세요", "알려줘",
    "보여주세요", "보여줘", "찾아주세요", "찾아줘", "조회", "확인", "정보",
    "있습니까", "있나요", "있는지", "있어", "해주세요", "해줘", "부탁해", "부탁",
  ].map(compact).sort((left, right) => right.length - left.length);

  for (const term of genericTerms) subject = subject.replaceAll(term, "");
  return subject.replace(/^(은|는|이|가|을|를|에|의|좀)+|(?:은|는|이|가|을|를|에|의|좀)+$/g, "");
}

function displayRecallSubject(text: string): string {
  return text
    .replace(/(자동차리콜센터|리콜\s*(정보|조회|확인)?|조회해\s*주세요|조회해\s*줘|확인해\s*주세요|확인해\s*줘|알려\s*주세요|알려\s*줘|보여\s*주세요|보여\s*줘|찾아\s*주세요|찾아\s*줘|있습니까|있나요|있는지|있어)/g, " ")
    .replace(/[,.!?()[\]{}]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractYears(text: string): number[] {
  return [...text.matchAll(/(?:19|20)\d{2}/g)].map((match) => Number(match[0]));
}

export function resolveRecallTarget(
  text: string,
  vehicles: VehicleProfile[],
  activeVehicle: VehicleProfile,
): RecallTargetResolution {
  const normalizedText = compact(text);
  const requestedYears = extractYears(text);
  const matches = vehicles.filter((vehicle) => {
    if (requestedYears.length && !requestedYears.includes(vehicle.modelYear)) return false;
    return identityTerms(vehicle).some((term) => normalizedText.includes(term));
  });

  if (matches.length === 1) return { kind: "explicit", vehicle: matches[0] };
  if (matches.length > 1) return { kind: "ambiguous", vehicles: matches };

  const subject = remainingRecallSubject(text);
  if (!subject) return { kind: "active", vehicle: activeVehicle };

  const manufacturerMatches = vehicles.filter((vehicle) => compact(vehicle.manufacturer) === subject);
  if (manufacturerMatches.length === 1) return { kind: "explicit", vehicle: manufacturerMatches[0] };
  if (manufacturerMatches.length > 1) return { kind: "ambiguous", vehicles: manufacturerMatches };

  return { kind: "missing", query: displayRecallSubject(text) || subject };
}
