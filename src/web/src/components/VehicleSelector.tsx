import { ChevronIcon, PlusIcon } from "./Icons";
import { getEnergyLabel, getVehicleTitle } from "../lib/vehicle";
import type { VehicleSyncStatus } from "../hooks/useVehicleProfiles";
import type { VehicleProfile } from "../types";

interface VehicleSelectorProps {
  vehicles: VehicleProfile[];
  activeVehicle: VehicleProfile;
  syncStatus: VehicleSyncStatus;
  onSelect: (vehicleId: string) => Promise<void>;
  onManage: () => void;
}

export function VehicleSelector({ vehicles, activeVehicle, syncStatus, onSelect, onManage }: VehicleSelectorProps) {
  return (
    <div className="vehicle-selector">
      <label htmlFor="active-vehicle">활성 차량</label>
      <div className="vehicle-select-wrap">
        <select id="active-vehicle" value={activeVehicle.id} disabled={syncStatus.mode === "connecting"} onChange={(event) => void onSelect(event.target.value).catch(() => undefined)}>
          {vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{getVehicleTitle(vehicle)}</option>)}
        </select>
        <ChevronIcon className="select-icon" />
      </div>
      <span className="energy-tag">{getEnergyLabel(activeVehicle)}</span>
      <span className={`sync-tag sync-${syncStatus.mode}`} title={syncStatus.detail}>{syncStatus.label}</span>
      <button type="button" className="icon-button" onClick={onManage} aria-label="차량 프로필 관리"><PlusIcon /></button>
    </div>
  );
}
