import type { ReactNode } from "react";
import { BoltIcon, BookIcon, CarIcon, FuelIcon, RouteIcon, WrenchIcon } from "../../components/Icons";
import { FUEL_GRADE_LABELS, getVehicleTitle, isEv, isHydrogen } from "../../lib/vehicle";
import type { AppView, VehicleProfile } from "../../types";

interface DashboardProps { vehicle: VehicleProfile; onNavigate: (view: AppView) => void; }

export function Dashboard({ vehicle, onNavigate }: DashboardProps) {
  const electric = isEv(vehicle);
  const hydrogen = isHydrogen(vehicle);
  const plannerTitle = electric ? "EV 충전 플래너" : hydrogen ? "수소 충전 플래너" : "주유 경로 플래너";
  const plannerCopy = electric
    ? "경로의 충전소와 예상 충전·총 시간을 계산합니다."
    : hydrogen
      ? "경로 주변 수소충전소의 운영 상태와 우회 정보를 확인합니다."
      : `${vehicle.fuelGrade ? FUEL_GRADE_LABELS[vehicle.fuelGrade] : "지정 연료"} 취급 주유소를 경로에서 찾습니다.`;
  const cards: Array<{ title: string; copy: string; view: AppView; tone: string; icon: ReactNode }> = [
    { title: "경고등·증상", copy: "현재 증상을 입력하고 안전 행동부터 확인합니다.", view: "maintenance", tone: "blue", icon: <WrenchIcon /> },
    { title: "매뉴얼·리콜", copy: "차량 설명서와 공식 안전정보를 한곳에서 찾습니다.", view: "manual", tone: "green", icon: <BookIcon /> },
    { title: plannerTitle, copy: plannerCopy, view: "planner", tone: electric ? "purple" : hydrogen ? "hydrogen" : "orange", icon: electric ? <BoltIcon /> : <FuelIcon /> },
    { title: "중고차 분석", copy: "매물 자료와 점검 기록에서 위험 요인을 정리합니다.", view: "used-car", tone: "amber", icon: <CarIcon /> },
  ];

  return (
    <section className="page-section dashboard-page">
      <div className="page-heading">
        <div><p className="section-caption">{vehicle.nickname}</p><h1>오늘은 무엇을 확인할까요?</h1><p>{getVehicleTitle(vehicle)} 기준으로 모든 기능과 AI 대화가 연결됩니다.</p></div>
        <RouteIcon className="heading-mark" />
      </div>
      <div className="feature-grid">
        {cards.map((card) => (
          <button key={card.view} type="button" className={`feature-card tone-${card.tone}`} onClick={() => onNavigate(card.view)}>
            <span className="feature-icon">{card.icon}</span>
            <span className="feature-copy"><strong>{card.title}</strong><span>{card.copy}</span></span>
            <span className="feature-arrow" aria-hidden="true">→</span>
          </button>
        ))}
      </div>
      <div className="status-strip"><span className="status-dot" /><div><strong>차량 개인화는 FastAPI와 연결할 수 있습니다.</strong><span>지도·전기·수소 충전소·주유소 API와 AI 모델은 아직 연결하지 않았으며 샘플 상태만 표시합니다.</span></div></div>
    </section>
  );
}
