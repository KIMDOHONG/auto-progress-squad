import { useState, type FormEvent } from "react";
import { FUEL_GRADE_LABELS, POWERTRAIN_LABELS, getVehicleTitle } from "../../lib/vehicle";
import type { VehicleDraft, VehicleProfile } from "../../types";

const EMPTY_DRAFT: VehicleDraft = {
  nickname: "",
  manufacturer: "",
  model: "",
  modelYear: "2026",
  powertrain: "gasoline",
  fuelGrade: "regular",
  batteryCapacityKwh: "",
};

interface VehicleManagerProps {
  vehicles: VehicleProfile[];
  activeVehicleId: string;
  onClose: () => void;
  onSelect: (vehicleId: string) => Promise<void>;
  onAdd: (vehicle: VehicleProfile) => Promise<boolean>;
  onUpdate: (vehicle: VehicleProfile) => Promise<void>;
  onDelete: (vehicleId: string) => Promise<void>;
}

export function VehicleManager({ vehicles, activeVehicleId, onClose, onSelect, onAdd, onUpdate, onDelete }: VehicleManagerProps) {
  const [draft, setDraft] = useState<VehicleDraft>(EMPTY_DRAFT);
  const [editingVehicleId, setEditingVehicleId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const isElectric = draft.powertrain === "electric";
  const isHydrogen = draft.powertrain === "hydrogen";

  function updateDraft<Key extends keyof VehicleDraft>(key: Key, value: VehicleDraft[Key]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!draft.manufacturer.trim() || !draft.model.trim() || !draft.modelYear.trim()) {
      setError("제조사, 모델, 연식을 입력해 주세요.");
      return;
    }

    const vehicle: VehicleProfile = {
      id: editingVehicleId ?? crypto.randomUUID(),
      nickname: draft.nickname.trim() || draft.model.trim(),
      manufacturer: draft.manufacturer.trim(),
      model: draft.model.trim(),
      modelYear: Number(draft.modelYear),
      powertrain: draft.powertrain,
      ...(isElectric
        ? { batteryCapacityKwh: draft.batteryCapacityKwh ? Number(draft.batteryCapacityKwh) : undefined }
        : isHydrogen ? {} : { fuelGrade: draft.fuelGrade }),
    };

    setIsSaving(true);
    try {
      if (editingVehicleId) {
        await onUpdate(vehicle);
        setEditingVehicleId(null);
        setDraft(EMPTY_DRAFT);
        return;
      }

      if (!await onAdd(vehicle)) {
        setError("차량은 최대 3대까지 등록할 수 있습니다. 기존 차량을 삭제하거나 수정해 주세요.");
        return;
      }
      setDraft(EMPTY_DRAFT);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "차량 정보를 저장하지 못했습니다.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(vehicleId: string) {
    setError("");
    setIsSaving(true);
    try {
      await onDelete(vehicleId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "차량을 삭제하지 못했습니다.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSelect(vehicleId: string) {
    setError("");
    try {
      await onSelect(vehicleId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "활성 차량을 변경하지 못했습니다.");
    }
  }

  function startEditing(vehicle: VehicleProfile) {
    setEditingVehicleId(vehicle.id);
    setError("");
    setDraft({
      nickname: vehicle.nickname,
      manufacturer: vehicle.manufacturer,
      model: vehicle.model,
      modelYear: String(vehicle.modelYear),
      powertrain: vehicle.powertrain,
      fuelGrade: vehicle.fuelGrade ?? "regular",
      batteryCapacityKwh: vehicle.batteryCapacityKwh ? String(vehicle.batteryCapacityKwh) : "",
    });
  }

  function cancelEditing() {
    setEditingVehicleId(null);
    setError("");
    setDraft(EMPTY_DRAFT);
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="vehicle-modal" role="dialog" aria-modal="true" aria-labelledby="vehicle-manager-title">
        <header className="modal-header">
          <div><p className="section-caption">차량 프로필 {vehicles.length}/3</p><h2 id="vehicle-manager-title">내 차량 관리</h2></div>
          <button type="button" className="text-button" onClick={onClose}>닫기</button>
        </header>

        <div className="vehicle-list">
          {vehicles.map((vehicle) => (
            <article key={vehicle.id} className={vehicle.id === activeVehicleId ? "vehicle-row is-active" : "vehicle-row"}>
              <button type="button" className="vehicle-row-main" disabled={isSaving} onClick={() => void handleSelect(vehicle.id)}>
                <span className="vehicle-row-title">{vehicle.nickname}</span>
                <span>{getVehicleTitle(vehicle)} · {POWERTRAIN_LABELS[vehicle.powertrain]}</span>
              </button>
              <div className="vehicle-row-actions">
                <button type="button" className="text-button" disabled={isSaving} onClick={() => startEditing(vehicle)}>수정</button>
                <button type="button" className="danger-link" disabled={vehicles.length === 1 || isSaving} onClick={() => void handleDelete(vehicle.id)}>삭제</button>
              </div>
            </article>
          ))}
        </div>

        <form className="vehicle-form" onSubmit={handleSubmit}>
          <h3>{editingVehicleId ? "차량 정보 수정" : "새 차량 등록"}</h3>
          <div className="form-grid three-columns">
            <label>별명<input value={draft.nickname} onChange={(event) => updateDraft("nickname", event.target.value)} placeholder="예: 주말 차량" /></label>
            <label>제조사 *<input value={draft.manufacturer} onChange={(event) => updateDraft("manufacturer", event.target.value)} placeholder="예: BMW" /></label>
            <label>모델 *<input value={draft.model} onChange={(event) => updateDraft("model", event.target.value)} placeholder="예: 330i" /></label>
            <label>연식 *<input type="number" min="1990" max="2030" value={draft.modelYear} onChange={(event) => updateDraft("modelYear", event.target.value)} /></label>
            <label>동력원<select value={draft.powertrain} onChange={(event) => updateDraft("powertrain", event.target.value as VehicleDraft["powertrain"])}>{Object.entries(POWERTRAIN_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            {isElectric ? (
              <label>배터리 용량<input type="number" min="1" value={draft.batteryCapacityKwh} onChange={(event) => updateDraft("batteryCapacityKwh", event.target.value)} placeholder="kWh" /></label>
            ) : isHydrogen ? (
              <label>충전 연료<input value="수소" readOnly /></label>
            ) : (
              <label>지정 연료<select value={draft.fuelGrade} onChange={(event) => updateDraft("fuelGrade", event.target.value as VehicleDraft["fuelGrade"])}>{Object.entries(FUEL_GRADE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            )}
          </div>
          {error ? <p className="form-error" role="alert">{error}</p> : null}
          <div className="form-actions">
            <button type="submit" className="primary-button" disabled={isSaving}>{isSaving ? "저장 중…" : editingVehicleId ? "변경 저장" : "차량 등록"}</button>
            {editingVehicleId ? <button type="button" className="secondary-button" disabled={isSaving} onClick={cancelEditing}>수정 취소</button> : null}
          </div>
        </form>
      </section>
    </div>
  );
}
