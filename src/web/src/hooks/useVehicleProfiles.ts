import { useCallback, useMemo, useState } from "react";
import { DEFAULT_VEHICLES } from "../lib/vehicle";
import type { VehicleProfile } from "../types";

const STORAGE_KEY = "auto-squad.vehicle-profiles.v1";

interface StoredProfiles {
  version: 1;
  vehicles: VehicleProfile[];
  activeVehicleId: string;
}

function readStoredProfiles(): StoredProfiles {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) throw new Error("no stored profiles");
    const parsed = JSON.parse(raw) as StoredProfiles;
    if (parsed.version !== 1 || !Array.isArray(parsed.vehicles) || parsed.vehicles.length === 0) {
      throw new Error("invalid stored profiles");
    }
    return parsed;
  } catch {
    return { version: 1, vehicles: DEFAULT_VEHICLES, activeVehicleId: DEFAULT_VEHICLES[0].id };
  }
}

function persist(value: StoredProfiles): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
}

export function useVehicleProfiles() {
  const [state, setState] = useState<StoredProfiles>(readStoredProfiles);
  const activeVehicle = useMemo(
    () => state.vehicles.find((vehicle) => vehicle.id === state.activeVehicleId) ?? state.vehicles[0],
    [state.activeVehicleId, state.vehicles],
  );

  const updateState = useCallback((updater: (current: StoredProfiles) => StoredProfiles) => {
    setState((current) => {
      const next = updater(current);
      persist(next);
      return next;
    });
  }, []);

  const setActiveVehicle = useCallback((activeVehicleId: string) => {
    updateState((current) => ({ ...current, activeVehicleId }));
  }, [updateState]);

  const addVehicle = useCallback((vehicle: VehicleProfile) => {
    let added = false;
    updateState((current) => {
      if (current.vehicles.length >= 3) return current;
      added = true;
      return { ...current, vehicles: [...current.vehicles, vehicle], activeVehicleId: vehicle.id };
    });
    return added;
  }, [updateState]);

  const updateVehicle = useCallback((vehicle: VehicleProfile) => {
    updateState((current) => ({
      ...current,
      vehicles: current.vehicles.map((item) => item.id === vehicle.id ? vehicle : item),
    }));
  }, [updateState]);

  const deleteVehicle = useCallback((vehicleId: string) => {
    updateState((current) => {
      if (current.vehicles.length === 1) return current;
      const vehicles = current.vehicles.filter((vehicle) => vehicle.id !== vehicleId);
      const activeVehicleId = current.activeVehicleId === vehicleId ? vehicles[0].id : current.activeVehicleId;
      return { ...current, vehicles, activeVehicleId };
    });
  }, [updateState]);

  return { vehicles: state.vehicles, activeVehicle, setActiveVehicle, addVehicle, updateVehicle, deleteVehicle };
}
