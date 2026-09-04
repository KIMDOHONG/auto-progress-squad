import { useMemo, useState, type FormEvent } from "react";
import { BoltIcon, FuelIcon, RouteIcon } from "../../components/Icons";
import {
  calculateEvPlan,
  calculateFuelPlan,
  calculateRangePlan,
  type EnergyFillMode,
  type EvPlannerResult,
  type FuelPlannerResult,
  type FuelRefuelMode,
  type RangePlannerResult,
} from "../../lib/planner";
import {
  combineRoundTripRoutes,
  getPlannerMapConfig,
  lookupApiRoute,
  lookupApiStations,
  resolveApiLocation,
  reverseApiLocation,
  RouteApiError,
  type RouteAlternativeResult,
  type RouteLocationResult,
  type RouteLookupResult,
  type RouteOption,
  type StationCandidateResult,
  type StationLookupResult,
} from "../../lib/routeApi";
import { FUEL_GRADE_LABELS, getVehicleTitle, isEv, isHydrogen } from "../../lib/vehicle";
import type { VehicleProfile } from "../../types";
import { RouteMap } from "./RouteMap";

interface DrivePlannerProps { vehicle: VehicleProfile; apiBaseUrl?: string; }

type PlannerResult = EvPlannerResult | FuelPlannerResult | RangePlannerResult;
type TripMode = "one-way" | "round-trip";

const ROUTE_OPTION_LABELS: Record<RouteOption, string> = {
  trafast: "실시간 빠른 길",
  traoptimal: "실시간 최적",
  traavoidtoll: "무료 우선",
};

function EvResultView({ result }: { result: EvPlannerResult }) {
  const arrivalLabel = result.arrivalSocWithoutChargePercent < 0
    ? `도달 불가 (${result.arrivalSocWithoutChargePercent}%)`
    : `${result.arrivalSocWithoutChargePercent}%`;
  const voluntarilyCharged = result.status === "sufficient" && result.plannedChargeKwh > 0;
  const decisionLabel = result.status === "sufficient"
    ? voluntarilyCharged ? "선택 충전" : "충전 불필요"
    : result.needsEnRouteStop ? "경로 중 충전 필요" : "출발 전 충전 필요";
  const decisionText = result.status === "sufficient"
    ? voluntarilyCharged
      ? "필수 충전은 아니지만 출발 전 100% 충전하는 선택으로 계산했습니다."
      : "현재 조건으로 최소 SoC를 지키며 도착할 수 있습니다."
    : result.needsEnRouteStop
      ? result.chargeMode === "full"
        ? `출발 전 100% 충전해도 부족하므로 경로 중 최소 ${result.enRouteChargeKwh} kWh를 추가 충전해야 합니다.`
        : `현재 배터리 ${result.currentSocPercent}%로 출발하면 경로 중 최소 ${result.enRouteChargeKwh} kWh를 추가 충전해야 합니다.`
      : `출발 전에 최소 ${result.requiredChargeKwh} kWh를 충전해야 합니다.`;

  return (
    <div className="result-body">
      <div className={`planner-decision ${result.status}`}>
        <span>{decisionLabel}</span>
        <strong>{decisionText}</strong>
      </div>
      <dl>
        <div><dt>예상 소비전력</dt><dd>{result.tripEnergyKwh} kWh</dd></div>
        <div><dt>충전 없이 도착 SoC</dt><dd>{arrivalLabel}</dd></div>
        <div><dt>최소 필요 충전량</dt><dd>{result.requiredChargeKwh} kWh</dd></div>
        <div><dt>선택 계획 충전량</dt><dd>{result.plannedChargeKwh} kWh</dd></div>
        <div><dt>출발 전 충전량</dt><dd>{result.departureChargeKwh} kWh</dd></div>
        <div><dt>경로 중 추가량</dt><dd>{result.enRouteChargeKwh} kWh</dd></div>
        <div><dt>계획 충전 후 도착 SoC</dt><dd>{result.arrivalSocAfterPlannedChargePercent}%</dd></div>
        <div><dt>최소 SoC까지 주행거리</dt><dd>{result.availableDistanceToReserveKm} km</dd></div>
      </dl>
      <div className="calculation-breakdown" aria-label="EV 계산 조건과 계산식">
        <strong>계산 조건·계산식</strong>
        <ul>
          <li>현재 에너지 = {result.batteryCapacityKwh} kWh × {result.currentSocPercent}% = {result.currentEnergyKwh} kWh</li>
          <li>경로 소비전력 = {result.routeDistanceKm} km ÷ {result.efficiencyKmPerKwh} km/kWh = {result.tripEnergyKwh} kWh</li>
          <li>도착 예상 SoC = {result.currentSocPercent}% - ({result.tripEnergyKwh} ÷ {result.batteryCapacityKwh} × 100) = {result.arrivalSocWithoutChargePercent}%</li>
          <li>최소 필요 충전량 = max(0, 소비전력 + 도착 예비전력 {result.reserveEnergyKwh} kWh - 현재 에너지) = {result.requiredChargeKwh} kWh</li>
          <li>계획 충전량 {result.plannedChargeKwh} kWh · {result.chargeMode === "full" ? "출발 전 100% 충전" : "필요한 만큼 충전"} 기준</li>
        </ul>
      </div>
    </div>
  );
}

function RangeResultView({ result, fuelLabel }: { result: RangePlannerResult; fuelLabel: string }) {
  const isHydrogenResult = result.kind === "hydrogen";
  const stopLabel = isHydrogenResult ? "수소 충전 필요" : "주유 필요";
  const enoughLabel = isHydrogenResult ? "수소 충전 없이 도착 가능" : "주유 없이 도착 가능";

  return (
    <div className="result-body">
      <div className={`planner-decision ${result.status}`}>
        <span>{result.status === "sufficient" ? "주행거리 충분" : stopLabel}</span>
        <strong>{result.status === "sufficient" ? enoughLabel : `목적지까지 최소 ${result.requiredAdditionalRangeKm} km의 추가 주행가능거리가 필요합니다.`}</strong>
      </div>
      <dl>
        <div><dt>입력 경로 거리</dt><dd>{result.routeDistanceKm} km</dd></div>
        <div><dt>현재 주행가능거리</dt><dd>{result.remainingRangeKm} km</dd></div>
        <div><dt>도착 예상 여유거리</dt><dd>{result.remainingMarginKm} km</dd></div>
        <div><dt>{isHydrogenResult ? "충전 연료" : "필수 연료"}</dt><dd>{fuelLabel}</dd></div>
      </dl>
      <div className="calculation-breakdown" aria-label="주행가능거리 계산 조건과 계산식">
        <strong>계산 조건·계산식</strong>
        <ul>
          <li>여유거리 = 현재 주행가능거리 {result.remainingRangeKm} km - 경로 거리 {result.routeDistanceKm} km</li>
          <li>{result.status === "sufficient" ? `도착 후 예상 여유거리 = ${result.remainingMarginKm} km` : `부족한 주행가능거리 = ${result.requiredAdditionalRangeKm} km`}</li>
        </ul>
      </div>
    </div>
  );
}

function FuelResultView({ result, fuelLabel }: { result: FuelPlannerResult; fuelLabel: string }) {
  const voluntarilyFilled = result.status === "sufficient" && result.plannedRefuelLiters > 0;
  const decisionLabel = result.status === "sufficient"
    ? voluntarilyFilled ? "선택 주유" : "주유 불필요"
    : result.needsEnRouteStop ? "경로 중 주유 필요" : "출발 전 주유 필요";
  const decisionText = result.status === "sufficient"
    ? voluntarilyFilled
      ? "필수 주유는 아니지만 출발 전 가득 주유하는 선택으로 계산했습니다."
      : "현재 연료로 도착 희망 잔량을 지키며 도착할 수 있습니다."
    : result.needsEnRouteStop
      ? `출발 전 가득 주유해도 부족하므로 경로 중 최소 ${result.enRouteRefuelLiters}L를 추가 주유해야 합니다.`
      : `출발 전에 최소 ${result.requiredRefuelLiters}L를 주유해야 합니다.`;

  return (
    <div className="result-body">
      <div className={`planner-decision ${result.status}`}>
        <span>{decisionLabel}</span>
        <strong>{decisionText}</strong>
      </div>
      <dl>
        <div><dt>예상 소비 연료</dt><dd>{result.tripFuelLiters} L</dd></div>
        <div><dt>최소 필요 주유량</dt><dd>{result.requiredRefuelLiters} L</dd></div>
        <div><dt>선택 계획 주유량</dt><dd>{result.plannedRefuelLiters} L</dd></div>
        <div><dt>예상 주유 비용</dt><dd>{result.plannedCostWon.toLocaleString()} 원</dd></div>
        <div><dt>출발 전 주유량</dt><dd>{result.departureRefuelLiters} L</dd></div>
        <div><dt>경로 중 추가량</dt><dd>{result.enRouteRefuelLiters} L</dd></div>
        <div><dt>도착 예상 잔량</dt><dd>{result.arrivalFuelLiters} L</dd></div>
        <div><dt>지정 연료</dt><dd>{fuelLabel}</dd></div>
      </dl>
      <div className="calculation-breakdown" aria-label="주유량 계산 조건과 계산식">
        <strong>계산 조건·계산식</strong>
        <ul>
          <li>예상 소비 연료 = {result.routeDistanceKm} km ÷ {result.efficiencyKmPerLiter} km/L = {result.tripFuelLiters} L</li>
          <li>최소 필요 주유량 = max(0, 소비 연료 + 도착 희망 {result.minimumArrivalFuelLiters} L - 현재 {result.currentFuelLiters} L) = {result.requiredRefuelLiters} L</li>
          <li>예상 비용 = 계획 주유량 {result.plannedRefuelLiters} L × 예상 단가 {result.fuelPriceWonPerLiter.toLocaleString()} 원/L = {result.plannedCostWon.toLocaleString()} 원</li>
          <li>탱크 용량 {result.fuelTankCapacityLiters} L · {result.refuelMode === "full" ? "출발 전 가득 주유" : "필요한 만큼 주유"} 기준</li>
        </ul>
      </div>
    </div>
  );
}

const STATION_STATUS_LABELS: Record<StationCandidateResult["status"], string> = {
  available: "이용 가능",
  busy: "혼잡",
  unavailable: "이용 불가",
  unknown: "상태 미확인",
};

function formatStationTimestamp(value: string) {
  const timestamp = new Date(value);
  return Number.isNaN(timestamp.getTime()) ? value : timestamp.toLocaleString("ko-KR");
}

function StationCandidateCard({ station, fuelLabel }: { station: StationCandidateResult; fuelLabel: string }) {
  const specifications = [
    station.powerKw !== null ? `최대 ${station.powerKw} kW` : null,
    station.pressureBar !== null ? `${station.pressureBar} bar` : null,
    station.fuelGradeMatch === "confirmed" ? `${fuelLabel} 취급 확인` : null,
    station.fuelGradeMatch === "unknown" ? `${fuelLabel} 취급 미확인` : null,
  ].filter(Boolean);

  return (
    <article className="station-candidate-card">
      <div className="station-candidate-heading">
        <div><strong>{station.name}</strong><span>{station.address}</span></div>
        <span className={`station-status ${station.status}`}>{STATION_STATUS_LABELS[station.status]}</span>
      </div>
      <div className="station-candidate-meta">
        <span>경로선에서 직선 약 {station.distanceToRouteKm} km</span>
        <span>전체 경로의 약 {station.routeProgressPercent}% 지점</span>
        {specifications.map((specification) => <span key={specification}>{specification}</span>)}
      </div>
      {station.statusObservedAt ? <small>상태 확인 시각: {formatStationTimestamp(station.statusObservedAt)}</small> : <small>상태 확인 시각 없음 · 방문 전 직접 확인 필요</small>}
      {station.sourceUrl ? <a href={station.sourceUrl} target="_blank" rel="noreferrer">공급자 원문 확인 ↗</a> : null}
    </article>
  );
}

function ExternalDataNotice({ kind, routeLookup, stationsIncluded }: { kind: PlannerResult["kind"]; routeLookup: RouteLookupResult | null; stationsIncluded: boolean }) {
  const missingData = stationsIncluded
    ? kind === "electric"
      ? "실시간 대기·충전곡선·예상 충전시간"
      : kind === "hydrogen"
        ? "실시간 대기·저장 탱크 잔량·실제 충전 가능량"
        : "실시간 가격·도로 우회거리"
    : kind === "electric"
      ? "충전소 위치·실시간 상태·충전곡선·충전시간"
      : kind === "hydrogen"
        ? "수소충전소 위치·운영 상태·대기 현황"
        : "주유소 위치·가격·지정연료 취급 여부";

  return (
    <div className="external-data-notice">
      <strong>{stationsIncluded ? "외부 데이터 일부 연동" : "외부 데이터 미연동"}</strong>
      <span>{routeLookup ? `경로 거리는 ${routeLookup.sourceName} 조회 결과를 사용했습니다.` : "이번 결과는 직접 입력한 거리만 사용한 로컬 계산입니다."} {missingData} 관련 정보는 결과에 포함하지 않았습니다.</span>
    </div>
  );
}

export function DrivePlanner({ vehicle, apiBaseUrl }: DrivePlannerProps) {
  const electric = isEv(vehicle);
  const hydrogen = isHydrogen(vehicle);
  const [departure, setDeparture] = useState(apiBaseUrl ? "" : "현재 위치");
  const [destination, setDestination] = useState(apiBaseUrl ? "" : "대한상공회의소 부산인력개발원");
  const [resolvedDeparture, setResolvedDeparture] = useState<RouteLocationResult | null>(null);
  const [resolvedDestination, setResolvedDestination] = useState<RouteLocationResult | null>(null);
  const [routeDistance, setRouteDistance] = useState("100");
  const [tripMode, setTripMode] = useState<TripMode>("one-way");
  const [batteryCapacity, setBatteryCapacity] = useState(vehicle.batteryCapacityKwh?.toString() ?? "");
  const [battery, setBattery] = useState("42");
  const [efficiency, setEfficiency] = useState("5.1");
  const [minimumArrivalSoc, setMinimumArrivalSoc] = useState("10");
  const [evChargeMode, setEvChargeMode] = useState<EnergyFillMode>("minimum");
  const [remainingRange, setRemainingRange] = useState("120");
  const [fuelTankCapacity, setFuelTankCapacity] = useState(vehicle.fuelTankCapacityLiters?.toString() ?? "");
  const [currentFuel, setCurrentFuel] = useState("20");
  const [fuelEfficiency, setFuelEfficiency] = useState("12");
  const [minimumArrivalFuel, setMinimumArrivalFuel] = useState("5");
  const [fuelPrice, setFuelPrice] = useState("1700");
  const [fuelRefuelMode, setFuelRefuelMode] = useState<FuelRefuelMode>("minimum");
  const [result, setResult] = useState<PlannerResult | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [routeLookup, setRouteLookup] = useState<RouteLookupResult | null>(null);
  const [routeError, setRouteError] = useState("");
  const [routeLoading, setRouteLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState<"departure" | "destination" | "gps" | null>(null);
  const [selectedRouteOption, setSelectedRouteOption] = useState<RouteOption>("trafast");
  const [mapBrowserClientId, setMapBrowserClientId] = useState<string | null>(null);
  const [stationCorridorKm, setStationCorridorKm] = useState("5");
  const [stationLookup, setStationLookup] = useState<StationLookupResult | null>(null);
  const [stationError, setStationError] = useState<{ code: string; message: string } | null>(null);
  const [stationLoading, setStationLoading] = useState(false);
  const fuelLabel = hydrogen ? "수소" : vehicle.fuelGrade ? FUEL_GRADE_LABELS[vehicle.fuelGrade] : "지정 연료";
  const routeAlternatives: RouteAlternativeResult[] = useMemo(() => routeLookup
    ? routeLookup.alternatives.length > 0 ? routeLookup.alternatives : [routeLookup]
    : [], [routeLookup]);
  const selectedRoute = routeAlternatives.find((route) => route.routeOption === selectedRouteOption)
    ?? routeAlternatives[0]
    ?? null;

  function clearStationLookup() {
    setStationLookup(null);
    setStationError(null);
  }

  function calculateForDistance(distance: string, chargeModeOverride?: EnergyFillMode) {
    const calculation = electric
      ? calculateEvPlan({
        routeDistanceKm: Number(distance),
        batteryCapacityKwh: Number(batteryCapacity),
        currentSocPercent: Number(battery),
        efficiencyKmPerKwh: Number(efficiency),
        minimumArrivalSocPercent: Number(minimumArrivalSoc),
        chargeMode: chargeModeOverride ?? evChargeMode,
      })
      : hydrogen
        ? calculateRangePlan({
        routeDistanceKm: Number(distance),
        remainingRangeKm: Number(remainingRange),
        kind: "hydrogen",
      })
        : calculateFuelPlan({
          routeDistanceKm: Number(distance),
          fuelTankCapacityLiters: Number(fuelTankCapacity),
          currentFuelLiters: Number(currentFuel),
          efficiencyKmPerLiter: Number(fuelEfficiency),
          minimumArrivalFuelLiters: Number(minimumArrivalFuel),
          fuelPriceWonPerLiter: Number(fuelPrice),
          refuelMode: fuelRefuelMode,
        });

    if (!calculation.ok) {
      setErrors(calculation.errors);
      setResult(null);
      return;
    }

    setErrors([]);
    setResult(calculation);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    calculateForDistance(routeDistance);
  }

  function selectEvChargeMode(mode: EnergyFillMode) {
    setEvChargeMode(mode);
    if (result?.kind === "electric") {
      calculateForDistance(routeDistance, mode);
    }
  }

  function clearRouteLookup() {
    setRouteLookup(null);
    setResult(null);
    setSelectedRouteOption("trafast");
    setRouteError("");
    setMapBrowserClientId(null);
    clearStationLookup();
  }

  async function handleLocationResolve(field: "departure" | "destination") {
    if (!apiBaseUrl) return;
    const query = field === "departure" ? departure.trim() : destination.trim();
    if (query.length < 2) {
      setRouteError(`${field === "departure" ? "출발지" : "목적지"}의 정확한 도로명 주소를 2자 이상 입력해 주세요.`);
      return;
    }
    setLocationLoading(field);
    setRouteError("");
    try {
      const location = await resolveApiLocation(apiBaseUrl, query, field);
      if (field === "departure") {
        setDeparture(location.address);
        setResolvedDeparture(location);
      } else {
        setDestination(location.address);
        setResolvedDestination(location);
      }
      clearRouteLookup();
    } catch (error) {
      if (field === "departure") setResolvedDeparture(null);
      else setResolvedDestination(null);
      setRouteError(error instanceof Error ? error.message : "주소를 확인하지 못했습니다.");
    } finally {
      setLocationLoading(null);
    }
  }

  function handleCurrentLocation() {
    if (!apiBaseUrl) return;
    if (!navigator.geolocation) {
      setRouteError("이 브라우저에서는 GPS 현재 위치를 사용할 수 없습니다. 출발지 주소를 직접 입력해 주세요.");
      return;
    }
    setLocationLoading("gps");
    setRouteError("");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const longitude = position.coords.longitude;
        const latitude = position.coords.latitude;
        setDeparture(`GPS ${latitude.toFixed(6)}, ${longitude.toFixed(6)}`);
        setResolvedDeparture(null);
        clearRouteLookup();
        void reverseApiLocation(apiBaseUrl, longitude, latitude)
          .then((location) => {
            setDeparture(location.address);
            setResolvedDeparture(location);
            clearRouteLookup();
          })
          .catch((error: unknown) => {
            setResolvedDeparture(null);
            const message = error instanceof Error ? error.message : "현재 위치의 주소를 확인하지 못했습니다.";
            setRouteError(`GPS 좌표는 확인했지만 주소로 변환하지 못했습니다. ${message}`);
          })
          .finally(() => setLocationLoading(null));
      },
      (error) => {
        setLocationLoading(null);
        setResolvedDeparture(null);
        if (error.code === 1) {
          setRouteError("위치 권한이 거부되었습니다. 현재 앱을 연 브라우저의 위치 권한을 허용하거나 출발지 주소를 직접 입력해 주세요.");
        } else if (error.code === 2) {
          setRouteError("현재 앱을 연 브라우저에서 위치 정보를 사용할 수 없습니다. Windows 위치 서비스와 이 브라우저의 위치 권한을 확인해 주세요.");
        } else if (error.code === 3) {
          setRouteError("현재 위치 확인 시간이 초과되었습니다. Wi-Fi 연결과 Windows 위치 서비스를 확인한 뒤 다시 시도해 주세요.");
        } else {
          setRouteError("현재 위치를 확인하지 못했습니다. 출발지 주소를 직접 입력해 주세요.");
        }
      },
      { enableHighAccuracy: false, timeout: 20_000, maximumAge: 300_000 },
    );
  }

  async function handleRouteLookup() {
    if (!apiBaseUrl) return;
    if (!resolvedDeparture || !resolvedDestination) {
      setRouteError("출발지와 목적지의 주소 확인을 먼저 완료해 주세요. 직접 입력 거리 계산은 계속 사용할 수 있습니다.");
      return;
    }
    setRouteLoading(true);
    setRouteError("");
    clearStationLookup();
    try {
      const routePromise = tripMode === "round-trip"
        ? Promise.all([
            lookupApiRoute(apiBaseUrl, resolvedDeparture, resolvedDestination),
            lookupApiRoute(apiBaseUrl, resolvedDestination, resolvedDeparture),
          ]).then(([outbound, inbound]) => combineRoundTripRoutes(outbound, inbound))
        : lookupApiRoute(apiBaseUrl, resolvedDeparture, resolvedDestination);
      const [lookup, mapConfig] = await Promise.all([
        routePromise,
        getPlannerMapConfig(apiBaseUrl).catch(() => ({ enabled: false, browserClientId: null })),
      ]);
      const distance = String(lookup.distanceKm);
      setRouteLookup(lookup);
      setSelectedRouteOption(lookup.routeOption);
      setMapBrowserClientId(mapConfig.enabled ? mapConfig.browserClientId : null);
      setRouteDistance(distance);
      calculateForDistance(distance);
    } catch (error) {
      setRouteLookup(null);
      setRouteError(error instanceof Error ? error.message : "실제 경로를 조회하지 못했습니다. 직접 입력 거리로 계산해 주세요.");
    } finally {
      setRouteLoading(false);
    }
  }

  function selectRoute(route: RouteAlternativeResult) {
    setSelectedRouteOption(route.routeOption);
    const distance = String(route.distanceKm);
    setRouteDistance(distance);
    calculateForDistance(distance);
    clearStationLookup();
  }

  async function handleStationLookup() {
    if (!apiBaseUrl || !selectedRoute || selectedRoute.path.length < 2) return;
    setStationLoading(true);
    setStationError(null);
    try {
      const lookup = await lookupApiStations(apiBaseUrl, {
        energyKind: electric ? "electric" : hydrogen ? "hydrogen" : "fuel",
        routePath: selectedRoute.path,
        corridorKm: Number(stationCorridorKm),
        limit: 5,
        fuelGrade: electric || hydrogen ? undefined : vehicle.fuelGrade,
      });
      setStationLookup(lookup);
    } catch (error) {
      setStationLookup(null);
      setStationError(error instanceof RouteApiError
        ? { code: error.code, message: error.message }
        : { code: "station_lookup_error", message: "충전·주유소 후보를 확인하지 못했습니다." });
    } finally {
      setStationLoading(false);
    }
  }

  return (
    <section className="page-section planner-page">
      <div className="page-heading compact">
        <div>
          <p className="section-caption">활성 차량 자동 분기 · 로컬 계산{apiBaseUrl ? " · 실제 경로 선택 조회" : ""}</p>
          <h1>{electric ? "EV 충전·주행 플래너" : hydrogen ? "수소 충전·주행 플래너" : "주유·주행 플래너"}</h1>
          <p>{getVehicleTitle(vehicle)} · {electric ? "배터리와 전비 기준" : hydrogen ? "현재 주행가능거리 기준" : `${fuelLabel}·연료량·평균 연비 기준`}</p>
        </div>
        <span className={electric ? "planner-symbol ev" : hydrogen ? "planner-symbol hydrogen" : "planner-symbol fuel"}>{electric ? <BoltIcon /> : <FuelIcon />}</span>
      </div>

      <form className="planner-form" onSubmit={handleSubmit} noValidate>
        <p className="planner-mode-note"><strong>{apiBaseUrl ? "정확한 주소 기반 경로 조회" : "수동 거리 모드"}</strong>{apiBaseUrl ? " 도로명과 건물번호를 확인한 뒤 실제 경로를 조회합니다. 실패해도 직접 입력 거리 계산은 유지됩니다." : " 출발지와 목적지는 경로 메모이며, 현재 계산에는 직접 입력한 거리만 사용합니다."}</p>
        <fieldset className="trip-mode-selector">
          <legend>여정 방식</legend>
          <label><input type="radio" name="trip-mode" value="one-way" checked={tripMode === "one-way"} onChange={() => { setTripMode("one-way"); clearRouteLookup(); }} />편도</label>
          <label><input type="radio" name="trip-mode" value="round-trip" checked={tripMode === "round-trip"} onChange={() => { setTripMode("round-trip"); clearRouteLookup(); }} />왕복</label>
          <span>{tripMode === "round-trip" ? "실제 경로는 가는 길과 오는 길을 각각 조회해 합산합니다. 직접 입력 시에는 왕복 총거리를 입력합니다." : "출발지에서 목적지까지 한 방향을 계산합니다."}</span>
        </fieldset>
        {apiBaseUrl ? (
          <div className="address-grid">
            <div className="address-field-group">
              <label htmlFor="planner-departure">출발지 정확한 주소<input id="planner-departure" placeholder="예: 부산광역시 연제구 중앙대로 1001" value={departure} onChange={(event) => { setDeparture(event.target.value); setResolvedDeparture(null); clearRouteLookup(); }} /></label>
              <div className="address-actions">
                <button type="button" className="inline-button" disabled={locationLoading !== null} onClick={() => void handleLocationResolve("departure")}>{locationLoading === "departure" ? "주소 확인 중…" : "출발지 주소 확인"}</button>
                <button type="button" className="inline-button location-button" disabled={locationLoading !== null} onClick={handleCurrentLocation}>{locationLoading === "gps" ? "현재 위치 확인 중…" : "GPS 현재 위치"}</button>
              </div>
              <span className={resolvedDeparture ? "address-confirmed" : "address-unconfirmed"}>{resolvedDeparture ? `확인됨 · ${resolvedDeparture.address}` : "주소 확인이 필요합니다."}</span>
            </div>
            <div className="address-field-group">
              <label htmlFor="planner-destination">목적지 정확한 주소<input id="planner-destination" placeholder="예: 경상남도 창원시 의창구 중앙대로 300" value={destination} onChange={(event) => { setDestination(event.target.value); setResolvedDestination(null); clearRouteLookup(); }} /></label>
              <div className="address-actions">
                <button type="button" className="inline-button" disabled={locationLoading !== null} onClick={() => void handleLocationResolve("destination")}>{locationLoading === "destination" ? "주소 확인 중…" : "목적지 주소 확인"}</button>
              </div>
              <span className={resolvedDestination ? "address-confirmed" : "address-unconfirmed"}>{resolvedDestination ? `확인됨 · ${resolvedDestination.address}` : "주소 확인이 필요합니다."}</span>
            </div>
          </div>
        ) : (
          <div className="form-grid route-inputs">
            <label htmlFor="planner-departure">출발지 메모<input id="planner-departure" value={departure} onChange={(event) => { setDeparture(event.target.value); clearRouteLookup(); }} /></label>
            <label htmlFor="planner-destination">목적지 메모<input id="planner-destination" value={destination} onChange={(event) => { setDestination(event.target.value); clearRouteLookup(); }} /></label>
          </div>
        )}
        <div className="form-grid route-inputs planner-measurements">
          <label htmlFor="planner-distance">{tripMode === "round-trip" ? "왕복 총 경로 거리" : "경로 거리"}<input id="planner-distance" type="number" min="0.1" step="0.1" value={routeDistance} onChange={(event) => { setRouteDistance(event.target.value); setRouteLookup(null); clearStationLookup(); }} /><span className="input-suffix" aria-hidden="true">km</span></label>
          {electric ? (
            <>
              <label htmlFor="planner-capacity">사용 가능 배터리 용량<input id="planner-capacity" type="number" min="0.1" step="0.1" value={batteryCapacity} onChange={(event) => setBatteryCapacity(event.target.value)} /><span className="input-suffix" aria-hidden="true">kWh</span></label>
              <label htmlFor="planner-soc">현재 SoC<input id="planner-soc" type="number" min="0" max="100" step="0.1" value={battery} onChange={(event) => setBattery(event.target.value)} /><span className="input-suffix" aria-hidden="true">%</span></label>
              <label htmlFor="planner-efficiency">최근 전비<input id="planner-efficiency" type="number" min="0.1" step="0.1" value={efficiency} onChange={(event) => setEfficiency(event.target.value)} /><span className="input-suffix" aria-hidden="true">km/kWh</span></label>
              <label htmlFor="planner-minimum-soc">도착 최소 SoC<input id="planner-minimum-soc" type="number" min="0" max="100" step="0.1" value={minimumArrivalSoc} onChange={(event) => setMinimumArrivalSoc(event.target.value)} /><span className="input-suffix" aria-hidden="true">%</span></label>
            </>
          ) : hydrogen ? (
            <>
              <label htmlFor="planner-remaining-range">현재 주행가능거리<input id="planner-remaining-range" type="number" min="0" step="0.1" value={remainingRange} onChange={(event) => setRemainingRange(event.target.value)} /><span className="input-suffix" aria-hidden="true">km</span></label>
              <label htmlFor="planner-fuel">충전 연료<input id="planner-fuel" value={fuelLabel} readOnly /></label>
            </>
          ) : (
            <>
              <label htmlFor="planner-tank-capacity">연료탱크 용량<input id="planner-tank-capacity" type="number" min="0.1" max="300" step="0.1" value={fuelTankCapacity} readOnly={vehicle.fuelTankCapacityLiters !== undefined} onChange={(event) => setFuelTankCapacity(event.target.value)} /><span className="input-suffix" aria-hidden="true">L</span></label>
              <label htmlFor="planner-current-fuel">현재 연료량<input id="planner-current-fuel" type="number" min="0" step="0.1" value={currentFuel} onChange={(event) => setCurrentFuel(event.target.value)} /><span className="input-suffix" aria-hidden="true">L</span></label>
              <label htmlFor="planner-fuel-efficiency">최근 평균 연비<input id="planner-fuel-efficiency" type="number" min="0.1" step="0.1" value={fuelEfficiency} onChange={(event) => setFuelEfficiency(event.target.value)} /><span className="input-suffix" aria-hidden="true">km/L</span></label>
              <label htmlFor="planner-arrival-fuel">도착 희망 잔량<input id="planner-arrival-fuel" type="number" min="0" step="0.1" value={minimumArrivalFuel} onChange={(event) => setMinimumArrivalFuel(event.target.value)} /><span className="input-suffix" aria-hidden="true">L</span></label>
              <label htmlFor="planner-fuel-price">예상 연료 단가<input id="planner-fuel-price" type="number" min="1" step="1" value={fuelPrice} onChange={(event) => setFuelPrice(event.target.value)} /><span className="input-suffix" aria-hidden="true">원/L</span></label>
              <label htmlFor="planner-fuel">지정 연료<input id="planner-fuel" value={fuelLabel} readOnly /></label>
            </>
          )}
        </div>
        {electric ? (
          <fieldset className="trip-mode-selector">
            <legend>충전 방식</legend>
            <label><input type="radio" name="energy-fill-mode" value="minimum" checked={evChargeMode === "minimum"} onChange={() => selectEvChargeMode("minimum")} />필요한 만큼 충전</label>
            <label><input type="radio" name="energy-fill-mode" value="full" checked={evChargeMode === "full"} onChange={() => selectEvChargeMode("full")} />출발 전 100% 충전</label>
            <span>필요한 만큼은 현재 SoC로 출발해 경로 중 필요한 충전량을, 100% 충전은 출발 전 충전량과 이후 추가량을 나눠 표시합니다.</span>
          </fieldset>
        ) : hydrogen ? (
          <fieldset className="trip-mode-selector">
            <legend>충전 방식</legend>
            <label><input type="radio" name="energy-fill-mode" checked disabled />가득 충전 원칙</label>
            <span>현재 플래너는 국내 운용 관행에 따라 가득 충전을 기본값으로 고정합니다. 실제 충전량은 차량 탱크 사양, 충전기 압력과 충전소 저장 탱크 잔량에 따라 달라질 수 있습니다.</span>
          </fieldset>
        ) : (
          <fieldset className="trip-mode-selector">
            <legend>주유 방식</legend>
            <label><input type="radio" name="energy-fill-mode" value="minimum" checked={fuelRefuelMode === "minimum"} onChange={() => setFuelRefuelMode("minimum")} />필요한 만큼 주유</label>
            <label><input type="radio" name="energy-fill-mode" value="full" checked={fuelRefuelMode === "full"} onChange={() => setFuelRefuelMode("full")} />출발 전 가득 주유</label>
            <span>가득 주유로도 부족하면 경로 중 추가로 필요한 양을 분리해 표시합니다.</span>
          </fieldset>
        )}
        {routeLookup && selectedRoute ? <div className="route-lookup-status" role="status"><strong>{routeLookup.sourceName} · {tripMode === "round-trip" ? "왕복 · " : ""}{ROUTE_OPTION_LABELS[selectedRoute.routeOption]}</strong><span>{selectedRoute.distanceKm} km · 약 {selectedRoute.durationMinutes}분 · 통행료 {selectedRoute.tollFare.toLocaleString()}원</span><span>{routeLookup.departure.address} → {routeLookup.destination.address}{tripMode === "round-trip" ? " → 출발지" : ""}</span></div> : null}
        {routeAlternatives.length > 1 ? (
          <div className="route-alternatives" aria-label="조회된 실제 경로 선택">
            {routeAlternatives.map((route) => (
              <button key={route.routeOption} type="button" className={route.routeOption === selectedRouteOption ? "route-option selected" : "route-option"} aria-pressed={route.routeOption === selectedRouteOption} onClick={() => selectRoute(route)}>
                <strong>{ROUTE_OPTION_LABELS[route.routeOption]}</strong>
                <span>{route.distanceKm}km · 약 {route.durationMinutes}분</span>
                <small>통행료 {route.tollFare.toLocaleString()}원</small>
              </button>
            ))}
          </div>
        ) : null}
        {routeError ? <div className="route-lookup-error" role="alert"><strong>주소·경로 확인 실패</strong><span>{routeError}</span></div> : null}
        {errors.length > 0 ? <div className="planner-errors" role="alert"><strong>입력값을 확인해 주세요.</strong><ul>{errors.map((error) => <li key={error}>{error}</li>)}</ul></div> : null}
        <div className="planner-actions">
          <button type="submit" className="primary-button"><RouteIcon />직접 입력 거리로 계산</button>
          {apiBaseUrl ? <button type="button" className="secondary-button" disabled={routeLoading} onClick={() => void handleRouteLookup()}><RouteIcon />{routeLoading ? "실제 경로 조회 중…" : "실제 경로 조회 후 계산"}</button> : null}
        </div>
      </form>

      <section className="station-candidates" aria-label="선택 경로 주변 충전·주유소 후보">
        <div className="station-candidates-header">
          <div>
            <p className="section-caption">선택 경로 기준</p>
            <h2>경로 주변 {electric ? "충전소" : hydrogen ? "수소충전소" : "주유소"} 후보</h2>
            <p>선택한 실제 경로선과 가까운 후보를 비교합니다. 표시 거리는 도로 우회거리가 아닌 경로선과의 직선거리입니다.</p>
          </div>
          <div className="station-search-controls">
            <label>탐색 반경
              <select value={stationCorridorKm} onChange={(event) => { setStationCorridorKm(event.target.value); clearStationLookup(); }}>
                <option value="2">2 km</option><option value="5">5 km</option><option value="10">10 km</option>
              </select>
            </label>
            <button type="button" className="secondary-button" disabled={!apiBaseUrl || !selectedRoute || stationLoading} onClick={() => void handleStationLookup()}>
              {stationLoading ? "후보 확인 중…" : `경로 주변 ${electric ? "충전소" : hydrogen ? "수소충전소" : "주유소"} 찾기`}
            </button>
          </div>
        </div>
        {!selectedRoute ? <p className="station-empty-state">주소 확인 후 실제 경로를 조회하면 주변 후보를 찾을 수 있습니다. 직접 입력 거리에는 경로 좌표가 없어 후보 조회를 제공하지 않습니다.</p> : null}
        {stationError ? (
          <div className="station-lookup-state warning" role="status">
            <strong>{stationError.code === "station_source_not_configured" ? "충전·주유소 공급자 미설정" : "후보 조회 실패"}</strong>
            <span>{stationError.message} 기존 주행 계산과 경로 결과는 그대로 유지됩니다.</span>
          </div>
        ) : null}
        {stationLookup?.status === "no_results" ? <div className="station-lookup-state"><strong>조건에 맞는 후보 없음</strong><span>경로선 반경 {stationLookup.corridorKm} km 안에서 후보를 찾지 못했습니다. 탐색 반경을 넓혀 다시 확인해 보세요.</span></div> : null}
        {stationLookup?.status === "matched" ? (
          <>
            <div className="station-source-summary"><strong>{stationLookup.sourceName}</strong><span>자료 시각 {formatStationTimestamp(stationLookup.retrievedAt)} · 반경 {stationLookup.corridorKm} km · {stationLookup.stations.length}곳</span><a href={stationLookup.sourceUrl} target="_blank" rel="noreferrer">데이터 출처 ↗</a></div>
            <div className="station-candidate-list">{stationLookup.stations.map((station) => <StationCandidateCard key={station.stationId} station={station} fuelLabel={fuelLabel} />)}</div>
            {stationLookup.warnings.length > 0 ? <ul className="station-warnings">{stationLookup.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}
          </>
        ) : null}
      </section>

      <div className="planner-content">
        {routeLookup && selectedRoute ? (
          <div className="route-canvas route-canvas-live">
            <RouteMap routes={routeAlternatives} selectedOption={selectedRoute.routeOption} browserClientId={mapBrowserClientId} />
            <div className="map-route-summary"><strong>{tripMode === "round-trip" ? "왕복 · " : ""}{ROUTE_OPTION_LABELS[selectedRoute.routeOption]}</strong><span>{routeLookup.departure.address} → {routeLookup.destination.address}{tripMode === "round-trip" ? " → 출발지" : ""}</span><span>{selectedRoute.distanceKm}km · 약 {selectedRoute.durationMinutes}분</span></div>
          </div>
        ) : (
          <div className="route-canvas" aria-label="수동 거리 경로 요약">
            <div className="route-line" />
            <span className="map-point start">출발</span><span className="map-point middle">경로</span><span className="map-point end">도착</span>
            <div className="map-empty-state"><RouteIcon /><strong>{tripMode === "round-trip" ? "직접 입력 왕복 거리" : "직접 입력 거리"}</strong><span>{departure || "출발지 미입력"} → {destination || "목적지 미입력"}{tripMode === "round-trip" ? " → 출발지" : ""} · {routeDistance || 0} km</span></div>
          </div>
        )}

        <aside className="planner-results" aria-label="로컬 플래너 계산 결과" aria-live="polite">
          <div className="result-header"><span className="local-badge">{routeLookup ? "API 거리 + 로컬 계산" : "로컬 계산"}</span><strong>{result ? "계산 완료" : "입력 후 계산해 주세요"}</strong></div>
          {result?.kind === "electric" ? <EvResultView result={result} /> : null}
          {result?.kind === "hydrogen" ? <RangeResultView result={result} fuelLabel={fuelLabel} /> : null}
          {result?.kind === "fuel" && "fuelTankCapacityLiters" in result ? <FuelResultView result={result} fuelLabel={fuelLabel} /> : null}
          {result ? <ExternalDataNotice kind={result.kind} routeLookup={routeLookup} stationsIncluded={stationLookup?.status === "matched"} /> : <p className="result-placeholder">입력한 거리와 활성 차량의 에너지 조건을 사용해 도착 가능 여부를 계산합니다.</p>}
          <p className="result-disclaimer">계산값은 날씨·속도·경사·공조 사용·배터리 또는 연료 상태 변화를 반영하지 않은 참고값입니다.</p>
        </aside>
      </div>
    </section>
  );
}
