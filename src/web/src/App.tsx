import { useState, type ReactNode } from "react";
import { BookIcon, CarIcon, FuelIcon, HomeIcon, RouteIcon, WrenchIcon } from "./components/Icons";
import { VehicleSelector } from "./components/VehicleSelector";
import { ChatPanel } from "./features/chat/ChatPanel";
import { Dashboard } from "./features/dashboard/Dashboard";
import { ManualHub } from "./features/manual/ManualHub";
import { DrivePlanner } from "./features/planner/DrivePlanner";
import { VehicleManager } from "./features/vehicles/VehicleManager";
import { useVehicleProfiles } from "./hooks/useVehicleProfiles";
import { isEv, isHydrogen } from "./lib/vehicle";
import type { AppView } from "./types";

const STATIC_PAGES: Record<Exclude<AppView, "dashboard" | "planner" | "manual">, { title: string; copy: string }> = {
  maintenance: { title: "경고등·증상 안전 대응", copy: "정비 규칙과 매뉴얼 근거를 연결하는 화면은 다음 기능 단계에서 구현합니다." },
  "used-car": { title: "중고차 위험 분석", copy: "성능점검표 업로드와 보험이력 입력 흐름을 다음 기능 단계에서 구현합니다." },
};

export default function App() {
  const [view, setView] = useState<AppView>("dashboard");
  const [vehicleManagerOpen, setVehicleManagerOpen] = useState(false);
  const { vehicles, activeVehicle, syncStatus, setActiveVehicle, addVehicle, updateVehicle, attachManualAdapter, replaceVehicle, deleteVehicle } = useVehicleProfiles();
  const plannerLabel = isEv(activeVehicle) ? "EV 충전 플래너" : isHydrogen(activeVehicle) ? "수소 충전 플래너" : "주유 경로 플래너";
  const navItems: Array<{ view: AppView; label: string; icon: ReactNode }> = [
    { view: "dashboard", label: "홈", icon: <HomeIcon /> },
    { view: "maintenance", label: "유지보수", icon: <WrenchIcon /> },
    { view: "manual", label: "매뉴얼·리콜", icon: <BookIcon /> },
    { view: "planner", label: plannerLabel, icon: isEv(activeVehicle) ? <RouteIcon /> : <FuelIcon /> },
    { view: "used-car", label: "중고차 분석", icon: <CarIcon /> },
  ];

  return (
    <div className="app">
      <header className="topbar">
        <button type="button" className="brand" onClick={() => setView("dashboard")}><span className="brand-mark">A</span><span><strong>AUTO SQUAD</strong><small>자동차 AI 코파일럿</small></span></button>
        <VehicleSelector vehicles={vehicles} activeVehicle={activeVehicle} syncStatus={syncStatus} onSelect={setActiveVehicle} onManage={() => setVehicleManagerOpen(true)} />
      </header>
      <div className="app-body">
        <nav className="sidebar" aria-label="주요 기능">
          {navItems.map((item) => <button key={item.view} type="button" className={view === item.view ? "nav-item is-active" : "nav-item"} onClick={() => setView(item.view)}>{item.icon}<span>{item.label}</span></button>)}
          <div className="sidebar-note"><span>현재 단계</span><strong>차량 API 연동</strong><small>FastAPI + SQLite</small></div>
        </nav>
        <main className="main-content">
          {view === "dashboard" ? <Dashboard vehicle={activeVehicle} onNavigate={setView} /> : null}
          {view === "planner" ? <DrivePlanner vehicle={activeVehicle} /> : null}
          {view === "manual" ? <ManualHub vehicle={activeVehicle} syncStatus={syncStatus} onAttachManualAdapter={attachManualAdapter} /> : null}
          {view === "maintenance" || view === "used-car" ? <section className="page-section placeholder-page"><p className="section-caption">다음 구현 단계</p><h1>{STATIC_PAGES[view].title}</h1><p>{STATIC_PAGES[view].copy}</p><div className="placeholder-rail"><span /><span /><span /></div></section> : null}
        </main>
        <ChatPanel vehicle={activeVehicle} vehicles={vehicles} view={view} onAddVehicle={addVehicle} onReplaceVehicle={replaceVehicle} onDeleteVehicle={deleteVehicle} />
      </div>
      {vehicleManagerOpen ? <VehicleManager vehicles={vehicles} activeVehicleId={activeVehicle.id} onClose={() => setVehicleManagerOpen(false)} onSelect={setActiveVehicle} onAdd={addVehicle} onUpdate={updateVehicle} onDelete={deleteVehicle} /> : null}
    </div>
  );
}
