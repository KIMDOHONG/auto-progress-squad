import { useMemo, useState, type FormEvent } from "react";
import { BoltIcon, FuelIcon, RouteIcon } from "../../components/Icons";
import { calculateEvPlan, calculateRangePlan, type EvPlannerResult, type RangePlannerResult } from "../../lib/planner";
import {
  getPlannerMapConfig,
  lookupApiRoute,
  resolveApiLocation,
  reverseApiLocation,
  type RouteAlternativeResult,
  type RouteLocationResult,
  type RouteLookupResult,
  type RouteOption,
} from "../../lib/routeApi";
import { FUEL_GRADE_LABELS, getVehicleTitle, isEv, isHydrogen } from "../../lib/vehicle";
import type { VehicleProfile } from "../../types";
import { RouteMap } from "./RouteMap";

interface DrivePlannerProps { vehicle: VehicleProfile; apiBaseUrl?: string; }

type PlannerResult = EvPlannerResult | RangePlannerResult;

const ROUTE_OPTION_LABELS: Record<RouteOption, string> = {
  trafast: "실시간 빠른 길",
  traoptimal: "실시간 최적",
  traavoidtoll: "무료 우선",
};

function EvResultView({ result }: { result: EvPlannerResult }) {
  const arrivalLabel = result.arrivalSocWithoutChargePercent < 0
    ? `도달 불가 (${result.arrivalSocWithoutChargePercent}%)`
    : `${result.arrivalSocWithoutChargePercent}%`;

  return (
    <div className="result-body">
      <div className={`planner-decision ${result.status}`}>
        <span>{result.status === "sufficient" ? "충전 불필요" : "충전 필요"}</span>
        <strong>{result.status === "sufficient" ? "현재 조건으로 최소 SoC를 지키며 도착할 수 있습니다." : "출발 전 또는 경로 중 충전이 필요합니다."}</strong>
      </div>
      <dl>
        <div><dt>예상 소비전력</dt><dd>{result.tripEnergyKwh} kWh</dd></div>
        <div><dt>충전 없이 도착 SoC</dt><dd>{arrivalLabel}</dd></div>
        <div><dt>최소 필요 충전량</dt><dd>{result.requiredChargeKwh} kWh</dd></div>
        <div><dt>최소 SoC까지 주행거리</dt><dd>{result.availableDistanceToReserveKm} km</dd></div>
      </dl>
      <div className="calculation-breakdown" aria-label="EV 계산 조건과 계산식">
        <strong>계산 조건·계산식</strong>
        <ul>
          <li>현재 에너지 = {result.batteryCapacityKwh} kWh × {result.currentSocPercent}% = {result.currentEnergyKwh} kWh</li>
          <li>경로 소비전력 = {result.routeDistanceKm} km ÷ {result.efficiencyKmPerKwh} km/kWh = {result.tripEnergyKwh} kWh</li>
          <li>도착 예상 SoC = {result.currentSocPercent}% - ({result.tripEnergyKwh} ÷ {result.batteryCapacityKwh} × 100) = {result.arrivalSocWithoutChargePercent}%</li>
          <li>최소 필요 충전량 = max(0, 소비전력 + 도착 예비전력 {result.reserveEnergyKwh} kWh - 현재 에너지) = {result.requiredChargeKwh} kWh</li>
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

function ExternalDataNotice({ kind, routeLookup }: { kind: PlannerResult["kind"]; routeLookup: RouteLookupResult | null }) {
  const missingData = kind === "electric"
    ? "충전소 위치·실시간 상태·충전곡선·충전시간"
    : kind === "hydrogen"
      ? "수소충전소 위치·운영 상태·대기 현황"
      : "주유소 위치·가격·지정연료 취급 여부";

  return (
    <div className="external-data-notice">
      <strong>외부 데이터 미연동</strong>
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
  const [batteryCapacity, setBatteryCapacity] = useState(vehicle.batteryCapacityKwh?.toString() ?? "");
  const [battery, setBattery] = useState("42");
  const [efficiency, setEfficiency] = useState("5.1");
  const [minimumArrivalSoc, setMinimumArrivalSoc] = useState("10");
  const [remainingRange, setRemainingRange] = useState("120");
  const [result, setResult] = useState<PlannerResult | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [routeLookup, setRouteLookup] = useState<RouteLookupResult | null>(null);
  const [routeError, setRouteError] = useState("");
  const [routeLoading, setRouteLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState<"departure" | "destination" | "gps" | null>(null);
  const [selectedRouteOption, setSelectedRouteOption] = useState<RouteOption>("trafast");
  const [mapBrowserClientId, setMapBrowserClientId] = useState<string | null>(null);
  const fuelLabel = hydrogen ? "수소" : vehicle.fuelGrade ? FUEL_GRADE_LABELS[vehicle.fuelGrade] : "지정 연료";
  const routeAlternatives: RouteAlternativeResult[] = useMemo(() => routeLookup
    ? routeLookup.alternatives.length > 0 ? routeLookup.alternatives : [routeLookup]
    : [], [routeLookup]);
  const selectedRoute = routeAlternatives.find((route) => route.routeOption === selectedRouteOption)
    ?? routeAlternatives[0]
    ?? null;

  function calculateForDistance(distance: string) {
    const calculation = electric
      ? calculateEvPlan({
        routeDistanceKm: Number(distance),
        batteryCapacityKwh: Number(batteryCapacity),
        currentSocPercent: Number(battery),
        efficiencyKmPerKwh: Number(efficiency),
        minimumArrivalSocPercent: Number(minimumArrivalSoc),
      })
      : calculateRangePlan({
        routeDistanceKm: Number(distance),
        remainingRangeKm: Number(remainingRange),
        kind: hydrogen ? "hydrogen" : "fuel",
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

  function clearRouteLookup() {
    setRouteLookup(null);
    setSelectedRouteOption("trafast");
    setRouteError("");
    setMapBrowserClientId(null);
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
    try {
      const [lookup, mapConfig] = await Promise.all([
        lookupApiRoute(apiBaseUrl, resolvedDeparture, resolvedDestination),
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
  }

  return (
    <section className="page-section planner-page">
      <div className="page-heading compact">
        <div>
          <p className="section-caption">활성 차량 자동 분기 · 로컬 계산{apiBaseUrl ? " · 실제 경로 선택 조회" : ""}</p>
          <h1>{electric ? "EV 충전·주행 플래너" : hydrogen ? "수소 충전·주행 플래너" : "특수연료 주유 경로 플래너"}</h1>
          <p>{getVehicleTitle(vehicle)} · {electric ? "배터리와 전비 기준" : hydrogen ? "현재 주행가능거리 기준" : `${fuelLabel} 기준`}</p>
        </div>
        <span className={electric ? "planner-symbol ev" : hydrogen ? "planner-symbol hydrogen" : "planner-symbol fuel"}>{electric ? <BoltIcon /> : <FuelIcon />}</span>
      </div>

      <form className="planner-form" onSubmit={handleSubmit} noValidate>
        <p className="planner-mode-note"><strong>{apiBaseUrl ? "정확한 주소 기반 경로 조회" : "수동 거리 모드"}</strong>{apiBaseUrl ? " 도로명과 건물번호를 확인한 뒤 실제 경로를 조회합니다. 실패해도 직접 입력 거리 계산은 유지됩니다." : " 출발지와 목적지는 경로 메모이며, 현재 계산에는 직접 입력한 거리만 사용합니다."}</p>
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
          <label htmlFor="planner-distance">경로 거리<input id="planner-distance" type="number" min="0.1" step="0.1" value={routeDistance} onChange={(event) => { setRouteDistance(event.target.value); setRouteLookup(null); }} /><span className="input-suffix" aria-hidden="true">km</span></label>
          {electric ? (
            <>
              <label htmlFor="planner-capacity">사용 가능 배터리 용량<input id="planner-capacity" type="number" min="0.1" step="0.1" value={batteryCapacity} onChange={(event) => setBatteryCapacity(event.target.value)} /><span className="input-suffix" aria-hidden="true">kWh</span></label>
              <label htmlFor="planner-soc">현재 SoC<input id="planner-soc" type="number" min="0" max="100" step="0.1" value={battery} onChange={(event) => setBattery(event.target.value)} /><span className="input-suffix" aria-hidden="true">%</span></label>
              <label htmlFor="planner-efficiency">최근 전비<input id="planner-efficiency" type="number" min="0.1" step="0.1" value={efficiency} onChange={(event) => setEfficiency(event.target.value)} /><span className="input-suffix" aria-hidden="true">km/kWh</span></label>
              <label htmlFor="planner-minimum-soc">도착 최소 SoC<input id="planner-minimum-soc" type="number" min="0" max="100" step="0.1" value={minimumArrivalSoc} onChange={(event) => setMinimumArrivalSoc(event.target.value)} /><span className="input-suffix" aria-hidden="true">%</span></label>
            </>
          ) : (
            <>
              <label htmlFor="planner-remaining-range">현재 주행가능거리<input id="planner-remaining-range" type="number" min="0" step="0.1" value={remainingRange} onChange={(event) => setRemainingRange(event.target.value)} /><span className="input-suffix" aria-hidden="true">km</span></label>
              <label htmlFor="planner-fuel">{hydrogen ? "충전 연료" : "검색 연료"}<input id="planner-fuel" value={fuelLabel} readOnly /></label>
            </>
          )}
        </div>
        {routeLookup && selectedRoute ? <div className="route-lookup-status" role="status"><strong>{routeLookup.sourceName} · {ROUTE_OPTION_LABELS[selectedRoute.routeOption]}</strong><span>{selectedRoute.distanceKm} km · 약 {selectedRoute.durationMinutes}분 · 통행료 {selectedRoute.tollFare.toLocaleString()}원</span><span>{routeLookup.departure.address} → {routeLookup.destination.address}</span></div> : null}
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

      <div className="planner-content">
        {routeLookup && selectedRoute ? (
          <div className="route-canvas route-canvas-live">
            <RouteMap routes={routeAlternatives} selectedOption={selectedRoute.routeOption} browserClientId={mapBrowserClientId} />
            <div className="map-route-summary"><strong>{ROUTE_OPTION_LABELS[selectedRoute.routeOption]}</strong><span>{routeLookup.departure.address} → {routeLookup.destination.address}</span><span>{selectedRoute.distanceKm}km · 약 {selectedRoute.durationMinutes}분</span></div>
          </div>
        ) : (
          <div className="route-canvas" aria-label="수동 거리 경로 요약">
            <div className="route-line" />
            <span className="map-point start">출발</span><span className="map-point middle">경로</span><span className="map-point end">도착</span>
            <div className="map-empty-state"><RouteIcon /><strong>직접 입력 거리</strong><span>{departure || "출발지 미입력"} → {destination || "목적지 미입력"} · {routeDistance || 0} km</span></div>
          </div>
        )}

        <aside className="planner-results" aria-label="로컬 플래너 계산 결과" aria-live="polite">
          <div className="result-header"><span className="local-badge">{routeLookup ? "API 거리 + 로컬 계산" : "로컬 계산"}</span><strong>{result ? "계산 완료" : "입력 후 계산해 주세요"}</strong></div>
          {result?.kind === "electric" ? <EvResultView result={result} /> : null}
          {result && result.kind !== "electric" ? <RangeResultView result={result} fuelLabel={fuelLabel} /> : null}
          {result ? <ExternalDataNotice kind={result.kind} routeLookup={routeLookup} /> : <p className="result-placeholder">입력한 거리와 활성 차량의 에너지 조건을 사용해 도착 가능 여부를 계산합니다.</p>}
          <p className="result-disclaimer">계산값은 날씨·속도·경사·공조 사용·배터리 또는 연료 상태 변화를 반영하지 않은 참고값입니다.</p>
        </aside>
      </div>
    </section>
  );
}
