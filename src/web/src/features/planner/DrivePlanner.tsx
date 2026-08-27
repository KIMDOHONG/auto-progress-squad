import { useMemo, useState, type FormEvent } from "react";
import { BoltIcon, FuelIcon, RouteIcon } from "../../components/Icons";
import { FUEL_GRADE_LABELS, getVehicleTitle, isEv, isHydrogen } from "../../lib/vehicle";
import type { VehicleProfile } from "../../types";

interface DrivePlannerProps { vehicle: VehicleProfile; }

const SAMPLE_STATIONS = [
  { name: "경로 주유소 A", detour: "우회 4분", availability: "취급 여부 API 연동 필요", tone: "recommended" },
  { name: "경로 주유소 B", detour: "우회 7분", availability: "취급 여부 미확인", tone: "pending" },
];

const SAMPLE_HYDROGEN_STATIONS = [
  { name: "경로 수소충전소 A", detour: "우회 6분", availability: "운영 상태·대기 차량 API 연동 필요", tone: "recommended" },
  { name: "경로 수소충전소 B", detour: "우회 11분", availability: "충전 가능 여부 미확인", tone: "pending" },
];

export function DrivePlanner({ vehicle }: DrivePlannerProps) {
  const electric = isEv(vehicle);
  const hydrogen = isHydrogen(vehicle);
  const [departure, setDeparture] = useState("현재 위치");
  const [destination, setDestination] = useState("대한상공회의소 부산인력개발원");
  const [battery, setBattery] = useState("42");
  const [efficiency, setEfficiency] = useState("5.1");
  const [remainingRange, setRemainingRange] = useState("120");
  const [submitted, setSubmitted] = useState(false);
  const fuelLabel = hydrogen ? "수소" : vehicle.fuelGrade ? FUEL_GRADE_LABELS[vehicle.fuelGrade] : "지정 연료";
  const estimate = useMemo(() => {
    const capacity = vehicle.batteryCapacityKwh ?? 77;
    return Math.max(0, Math.round(capacity * (Number(battery) / 100) * Number(efficiency || 0)));
  }, [battery, efficiency, vehicle.batteryCapacityKwh]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
  }

  return (
    <section className="page-section planner-page">
      <div className="page-heading compact">
        <div>
          <p className="section-caption">활성 차량 자동 분기</p>
          <h1>{electric ? "EV 충전·주행 플래너" : hydrogen ? "수소 충전·주행 플래너" : "특수연료 주유 경로 플래너"}</h1>
          <p>{getVehicleTitle(vehicle)} · {electric ? "배터리와 전비 기준" : hydrogen ? "수소충전소 운영 상태 우선 확인" : `${fuelLabel} 우선 검색`}</p>
        </div>
        <span className={electric ? "planner-symbol ev" : hydrogen ? "planner-symbol hydrogen" : "planner-symbol fuel"}>{electric ? <BoltIcon /> : <FuelIcon />}</span>
      </div>

      <form className="planner-form" onSubmit={handleSubmit}>
        <div className="form-grid route-inputs">
          <label>출발지<input value={departure} onChange={(event) => setDeparture(event.target.value)} required /></label>
          <label>목적지<input value={destination} onChange={(event) => setDestination(event.target.value)} required /></label>
          {electric ? (
            <>
              <label>현재 배터리<input type="number" min="0" max="100" value={battery} onChange={(event) => setBattery(event.target.value)} /><span className="input-suffix">%</span></label>
              <label>최근 전비<input type="number" min="0.1" step="0.1" value={efficiency} onChange={(event) => setEfficiency(event.target.value)} /><span className="input-suffix">km/kWh</span></label>
            </>
          ) : (
            <>
              <label>현재 주행가능거리<input type="number" min="0" value={remainingRange} onChange={(event) => setRemainingRange(event.target.value)} /><span className="input-suffix">km</span></label>
              <label>{hydrogen ? "충전 연료" : "검색 연료"}<input value={fuelLabel} readOnly /></label>
            </>
          )}
        </div>
        <button type="submit" className="primary-button"><RouteIcon />경로 계획 보기</button>
      </form>

      <div className="planner-content">
        <div className="route-canvas" aria-label="경로 지도 자리 표시 영역">
          <div className="route-line" />
          <span className="map-point start">출발</span><span className="map-point middle">경유</span><span className="map-point end">도착</span>
          <div className="map-empty-state"><RouteIcon /><strong>지도 API 연동 예정</strong><span>{departure} → {destination}</span></div>
        </div>

        <aside className="planner-results">
          <div className="result-header"><span className="demo-badge">샘플 결과</span><strong>{submitted ? "입력값 반영됨" : "경로를 입력해 주세요"}</strong></div>
          {electric ? (
            <div className="result-body">
              <dl><div><dt>현재 조건 예상 주행거리</dt><dd>{estimate} km</dd></div><div><dt>배터리 용량</dt><dd>{vehicle.batteryCapacityKwh ?? "미입력"} kWh</dd></div></dl>
              <article className="station-result"><BoltIcon /><div><strong>경로 충전소 A · 200 kW</strong><span>실시간 상태와 충전곡선 API 연동 전</span></div></article>
            </div>
          ) : hydrogen ? (
            <div className="result-body">
              <dl><div><dt>현재 주행가능거리</dt><dd>{remainingRange || 0} km</dd></div><div><dt>충전 연료</dt><dd>수소</dd></div></dl>
              {SAMPLE_HYDROGEN_STATIONS.map((station) => <article className={`station-result ${station.tone}`} key={station.name}><FuelIcon /><div><strong>{station.name}</strong><span>{station.detour} · {station.availability}</span></div></article>)}
            </div>
          ) : (
            <div className="result-body">
              <dl><div><dt>현재 주행가능거리</dt><dd>{remainingRange || 0} km</dd></div><div><dt>필수 연료</dt><dd>{fuelLabel}</dd></div></dl>
              {SAMPLE_STATIONS.map((station) => <article className={`station-result ${station.tone}`} key={station.name}><FuelIcon /><div><strong>{station.name}</strong><span>{station.detour} · {station.availability}</span></div></article>)}
            </div>
          )}
          <p className="result-disclaimer">실제 위치·영업시간·충전 가능 여부·연료 취급 여부는 외부 API 연결 후 출처와 조회 시각을 함께 표시합니다.</p>
        </aside>
      </div>
    </section>
  );
}
