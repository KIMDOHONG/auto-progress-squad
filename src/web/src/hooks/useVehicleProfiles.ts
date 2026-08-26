import { useCallback, useEffect, useMemo, useState } from "react";
import { DEFAULT_VEHICLES } from "../lib/vehicle";
import {
  activateApiVehicle,
  createApiVehicle,
  deleteApiVehicle,
  listApiVehicles,
  updateApiVehicle,
} from "../lib/vehicleApi";
import type { VehicleProfile } from "../types";

const STORAGE_KEY = "auto-squad.vehicle-profiles.v1";

interface StoredProfiles {
  version: 1;
  vehicles: VehicleProfile[];
  activeVehicleId: string;
}

export type VehicleSyncMode = "local" | "connecting" | "api" | "error";

export interface VehicleSyncStatus {
  mode: VehicleSyncMode;
  label: string;
  detail: string;
}

const LOCAL_STATUS: VehicleSyncStatus = {
  mode: "local",
  label: "브라우저 저장",
  detail: "공개 데모는 이 브라우저에만 차량 정보를 저장합니다.",
};

const connectionPromises = new Map<string, Promise<StoredProfiles>>();

function connectProfiles(apiBaseUrl: string, localState: StoredProfiles): Promise<StoredProfiles> {
  const existing = connectionPromises.get(apiBaseUrl);
  if (existing) return existing;

  const connection = (async () => {
    let remote = await listApiVehicles(apiBaseUrl);
    if (remote.vehicles.length === 0) {
      for (const vehicle of localState.vehicles) {
        await createApiVehicle(apiBaseUrl, vehicle);
      }
      if (localState.activeVehicleId !== localState.vehicles[0].id) {
        await activateApiVehicle(apiBaseUrl, localState.activeVehicleId);
      }
      remote = await listApiVehicles(apiBaseUrl);
    }
    if (remote.vehicles.length === 0) {
      throw new Error("동기화할 차량 정보가 없습니다.");
    }
    return {
      version: 1 as const,
      vehicles: remote.vehicles,
      activeVehicleId: remote.activeVehicleId ?? remote.vehicles[0].id,
    };
  })();

  connectionPromises.set(apiBaseUrl, connection);
  const release = () => {
    if (connectionPromises.get(apiBaseUrl) === connection) {
      connectionPromises.delete(apiBaseUrl);
    }
  };
  void connection.then(release, release);
  return connection;
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
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // Storage can be unavailable in private browsing or restricted environments.
  }
}

export function useVehicleProfiles() {
  const [state, setState] = useState<StoredProfiles>(readStoredProfiles);
  const [syncStatus, setSyncStatus] = useState<VehicleSyncStatus>(LOCAL_STATUS);
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").trim().replace(/\/$/, "");
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

  useEffect(() => {
    if (!apiBaseUrl) {
      setSyncStatus(LOCAL_STATUS);
      return;
    }

    let cancelled = false;
    async function connect() {
      setSyncStatus({ mode: "connecting", label: "API 연결 중", detail: "SQLite 차량 정보를 확인하고 있습니다." });
      try {
        const next = await connectProfiles(apiBaseUrl, state);
        if (cancelled) return;
        persist(next);
        setState(next);
        setSyncStatus({ mode: "api", label: "SQLite 동기화", detail: "차량 정보가 FastAPI와 동기화됩니다." });
      } catch {
        if (!cancelled) {
          setSyncStatus({ mode: "error", label: "로컬 대체 모드", detail: "API 연결에 실패해 이 브라우저에만 저장합니다." });
        }
      }
    }
    void connect();
    return () => { cancelled = true; };
  }, [apiBaseUrl]);

  const runApiAction = useCallback(async (action: () => Promise<void>) => {
    if (syncStatus.mode !== "api") return;
    try {
      await action();
    } catch (error) {
      setSyncStatus({ mode: "error", label: "로컬 대체 모드", detail: "API 요청에 실패해 이후 변경은 이 브라우저에만 저장합니다." });
      throw error;
    }
  }, [syncStatus.mode]);

  const setActiveVehicle = useCallback(async (activeVehicleId: string) => {
    await runApiAction(() => activateApiVehicle(apiBaseUrl, activeVehicleId));
    updateState((current) => ({ ...current, activeVehicleId }));
  }, [apiBaseUrl, runApiAction, updateState]);

  const addVehicle = useCallback(async (vehicle: VehicleProfile) => {
    if (state.vehicles.length >= 3) return false;
    await runApiAction(async () => {
      await createApiVehicle(apiBaseUrl, vehicle);
      await activateApiVehicle(apiBaseUrl, vehicle.id);
    });
    updateState((current) => ({ ...current, vehicles: [...current.vehicles, vehicle], activeVehicleId: vehicle.id }));
    return true;
  }, [apiBaseUrl, runApiAction, state.vehicles.length, updateState]);

  const updateVehicle = useCallback(async (vehicle: VehicleProfile) => {
    await runApiAction(() => updateApiVehicle(apiBaseUrl, vehicle).then(() => undefined));
    updateState((current) => ({
      ...current,
      vehicles: current.vehicles.map((item) => item.id === vehicle.id ? vehicle : item),
    }));
  }, [apiBaseUrl, runApiAction, updateState]);

  const deleteVehicle = useCallback(async (vehicleId: string) => {
    await runApiAction(() => deleteApiVehicle(apiBaseUrl, vehicleId));
    updateState((current) => {
      if (current.vehicles.length === 1) return current;
      const vehicles = current.vehicles.filter((vehicle) => vehicle.id !== vehicleId);
      const activeVehicleId = current.activeVehicleId === vehicleId ? vehicles[0].id : current.activeVehicleId;
      return { ...current, vehicles, activeVehicleId };
    });
  }, [apiBaseUrl, runApiAction, updateState]);

  return { vehicles: state.vehicles, activeVehicle, syncStatus, setActiveVehicle, addVehicle, updateVehicle, deleteVehicle };
}
