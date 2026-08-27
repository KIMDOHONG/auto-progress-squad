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

const STORAGE_KEY = "auto-squad.vehicle-profiles.v4";
const LEGACY_V3_STORAGE_KEY = "auto-squad.vehicle-profiles.v3";
const LEGACY_V2_STORAGE_KEY = "auto-squad.vehicle-profiles.v2";
const LEGACY_V1_STORAGE_KEY = "auto-squad.vehicle-profiles.v1";

interface StoredProfiles {
  version: 4;
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
      version: 4 as const,
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

interface LegacyV1StoredProfiles {
  version: 1;
  vehicles: VehicleProfile[];
  activeVehicleId: string;
}

interface LegacyV2StoredProfiles {
  version: 2;
  vehicles: VehicleProfile[];
  activeVehicleId: string;
}

interface LegacyV3StoredProfiles {
  version: 3;
  vehicles: VehicleProfile[];
  activeVehicleId: string;
}

const LEGACY_DEFAULTS = JSON.stringify([
  {
    id: "sample-ioniq5",
    nickname: "출퇴근 EV",
    manufacturer: "현대",
    model: "아이오닉 5",
    modelYear: 2024,
    powertrain: "electric",
    batteryCapacityKwh: 84,
  },
  {
    id: "sample-bmw3",
    nickname: "주말 차량",
    manufacturer: "BMW",
    model: "330i",
    modelYear: 2022,
    powertrain: "gasoline",
    fuelGrade: "premium",
  },
]);

const V2_DEFAULTS = JSON.stringify([
  {
    id: "sample-nexo",
    nickname: "가족 수소차",
    manufacturer: "현대",
    model: "넥쏘",
    modelYear: 2021,
    powertrain: "hydrogen",
  },
  {
    id: "sample-ioniq5n",
    nickname: "고성능 EV",
    manufacturer: "현대",
    model: "아이오닉 5 N",
    modelYear: 2024,
    powertrain: "electric",
    batteryCapacityKwh: 84,
  },
  {
    id: "sample-bmwm3",
    nickname: "주말 차량",
    manufacturer: "BMW",
    model: "M3",
    modelYear: 2021,
    powertrain: "gasoline",
    fuelGrade: "premium",
  },
]);

const V3_DEFAULTS = JSON.stringify([
  {
    id: "sample-nexo",
    nickname: "가족 수소차",
    manufacturer: "현대",
    model: "넥쏘",
    modelYear: 2021,
    powertrain: "hydrogen",
  },
  {
    id: "sample-electrified-gv70",
    nickname: "프리미엄 EV",
    manufacturer: "제네시스",
    model: "ELECTRIFIED GV70",
    modelYear: 2027,
    powertrain: "electric",
    batteryCapacityKwh: 84,
  },
  {
    id: "sample-bmwm3",
    nickname: "주말 차량",
    manufacturer: "BMW",
    model: "M3",
    modelYear: 2021,
    powertrain: "gasoline",
    fuelGrade: "premium",
  },
]);

function fallbackProfiles(): StoredProfiles {
  return { version: 4, vehicles: DEFAULT_VEHICLES, activeVehicleId: DEFAULT_VEHICLES[0].id };
}

function isValidProfiles(value: StoredProfiles | LegacyV1StoredProfiles | LegacyV2StoredProfiles | LegacyV3StoredProfiles): boolean {
  return Array.isArray(value.vehicles)
    && value.vehicles.length > 0
    && value.vehicles.some((vehicle) => vehicle.id === value.activeVehicleId);
}

function migrateV3Profiles(): StoredProfiles | null {
  try {
    const raw = window.localStorage.getItem(LEGACY_V3_STORAGE_KEY);
    if (!raw) return null;
    const legacy = JSON.parse(raw) as LegacyV3StoredProfiles;
    if (legacy.version !== 3 || !isValidProfiles(legacy)) return null;
    const migrated: StoredProfiles = {
      version: 4,
      vehicles: JSON.stringify(legacy.vehicles) === V3_DEFAULTS ? DEFAULT_VEHICLES : legacy.vehicles,
      activeVehicleId: legacy.activeVehicleId,
    };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(migrated));
    window.localStorage.removeItem(LEGACY_V3_STORAGE_KEY);
    return migrated;
  } catch {
    return null;
  }
}

function migrateV2Profiles(): StoredProfiles | null {
  try {
    const raw = window.localStorage.getItem(LEGACY_V2_STORAGE_KEY);
    if (!raw) return null;
    const legacy = JSON.parse(raw) as LegacyV2StoredProfiles;
    if (legacy.version !== 2 || !isValidProfiles(legacy)) return null;
    const unchangedDefaults = JSON.stringify(legacy.vehicles) === V2_DEFAULTS;
    const activeVehicleId = unchangedDefaults && legacy.activeVehicleId === "sample-ioniq5n"
      ? "sample-electrified-gv70"
      : legacy.activeVehicleId;
    const migrated: StoredProfiles = unchangedDefaults
      ? { version: 4, vehicles: DEFAULT_VEHICLES, activeVehicleId }
      : { version: 4, vehicles: legacy.vehicles, activeVehicleId };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(migrated));
    window.localStorage.removeItem(LEGACY_V2_STORAGE_KEY);
    return migrated;
  } catch {
    return null;
  }
}

function migrateV1Profiles(): StoredProfiles | null {
  try {
    const raw = window.localStorage.getItem(LEGACY_V1_STORAGE_KEY);
    if (!raw) return null;
    const legacy = JSON.parse(raw) as LegacyV1StoredProfiles;
    if (legacy.version !== 1 || !isValidProfiles(legacy)) return null;
    const migrated = JSON.stringify(legacy.vehicles) === LEGACY_DEFAULTS
      ? fallbackProfiles()
      : { version: 4 as const, vehicles: legacy.vehicles, activeVehicleId: legacy.activeVehicleId };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(migrated));
    window.localStorage.removeItem(LEGACY_V1_STORAGE_KEY);
    return migrated;
  } catch {
    return null;
  }
}

function readStoredProfiles(): StoredProfiles {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as StoredProfiles;
      if (parsed.version === 4 && isValidProfiles(parsed)) return parsed;
    }
  } catch {
    // Fall through to the versioned migration and defaults.
  }
  return migrateV3Profiles() ?? migrateV2Profiles() ?? migrateV1Profiles() ?? fallbackProfiles();
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

  const replaceVehicle = useCallback(async (vehicleId: string, replacement: VehicleProfile) => {
    const vehicle = { ...replacement, id: vehicleId };
    await runApiAction(async () => {
      await updateApiVehicle(apiBaseUrl, vehicle);
      await activateApiVehicle(apiBaseUrl, vehicleId);
    });
    updateState((current) => ({
      ...current,
      vehicles: current.vehicles.map((item) => item.id === vehicleId ? vehicle : item),
      activeVehicleId: vehicleId,
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

  return { vehicles: state.vehicles, activeVehicle, syncStatus, setActiveVehicle, addVehicle, updateVehicle, replaceVehicle, deleteVehicle };
}
