import { ChevronIcon, PlusIcon } from "./Icons";
import { getEnergyLabel, getVehicleTitle } from "../lib/vehicle";
import type { VehicleProfile } from "../types";

interface VehicleSelectorProps {
  vehicles: VehicleProfile[];
  activeVehicle: VehicleProfile;
  onSelect: (vehicleId: string) => void;
  onManage: () => void;
}

export function VehicleSelector({ vehicles, activeVehicle, onSelect, onManage }: VehicleSelectorProps) {
  return (
    <div className="vehicle-selector">
      <label htmlFor="active-vehicle">활성 차량</label>
      <div className="vehicle-select-wrap">
        <select id="active-vehicle" value={activeVehicle.id} onChange={(event) => onSelect(event.target.value)}>
          {vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{getVehicleTitle(vehicle)}</option>)}
        </select>
        <ChevronIcon className="select-icon" />
      </div>
      <span className="energy-tag">{getEnergyLabel(activeVehicle)}</span>
      <button type="button" className="icon-button" onClick={onManage} aria-label="차량 프로필 관리"><PlusIcon /></button>
    </div>
  );
}
