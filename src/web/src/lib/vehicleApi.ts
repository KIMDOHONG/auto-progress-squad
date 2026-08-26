import type { VehicleProfile } from "../types";

interface ApiVehicleProfile {
  id: string;
  nickname: string;
  manufacturer: string;
  model: string;
  model_year: number;
  powertrain: VehicleProfile["powertrain"];
  fuel_grade: VehicleProfile["fuelGrade"] | null;
  battery_capacity_kwh: number | null;
  is_active: boolean;
}

interface ApiVehicleList {
  items: ApiVehicleProfile[];
  active_vehicle_id: string | null;
}

interface ApiErrorPayload {
  error?: { code?: string; message?: string };
}

export class VehicleApiError extends Error {
  constructor(public readonly code: string, message: string) {
    super(message);
  }
}

function fromApi(vehicle: ApiVehicleProfile): VehicleProfile {
  return {
    id: vehicle.id,
    nickname: vehicle.nickname,
    manufacturer: vehicle.manufacturer,
    model: vehicle.model,
    modelYear: vehicle.model_year,
    powertrain: vehicle.powertrain,
    ...(vehicle.fuel_grade ? { fuelGrade: vehicle.fuel_grade } : {}),
    ...(vehicle.battery_capacity_kwh
      ? { batteryCapacityKwh: vehicle.battery_capacity_kwh }
      : {}),
  };
}

function toApi(vehicle: VehicleProfile) {
  return {
    nickname: vehicle.nickname,
    manufacturer: vehicle.manufacturer,
    model: vehicle.model,
    model_year: vehicle.modelYear,
    powertrain: vehicle.powertrain,
    fuel_grade: vehicle.fuelGrade ?? null,
    battery_capacity_kwh: vehicle.batteryCapacityKwh ?? null,
  };
}

async function request<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
    });
  } catch {
    throw new VehicleApiError("network_error", "백엔드 API에 연결할 수 없습니다.");
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as ApiErrorPayload;
    throw new VehicleApiError(
      payload.error?.code ?? "api_error",
      payload.error?.message ?? "차량 정보를 처리하지 못했습니다.",
    );
  }

  return (response.status === 204 ? undefined : await response.json()) as T;
}

export async function listApiVehicles(baseUrl: string) {
  const response = await request<ApiVehicleList>(baseUrl, "/api/v1/vehicles");
  return {
    vehicles: response.items.map(fromApi),
    activeVehicleId: response.active_vehicle_id,
  };
}

export async function createApiVehicle(baseUrl: string, vehicle: VehicleProfile) {
  const response = await request<ApiVehicleProfile>(baseUrl, "/api/v1/vehicles", {
    method: "POST",
    body: JSON.stringify({ id: vehicle.id, ...toApi(vehicle) }),
  });
  return fromApi(response);
}

export async function updateApiVehicle(baseUrl: string, vehicle: VehicleProfile) {
  const response = await request<ApiVehicleProfile>(baseUrl, `/api/v1/vehicles/${encodeURIComponent(vehicle.id)}`, {
    method: "PUT",
    body: JSON.stringify(toApi(vehicle)),
  });
  return fromApi(response);
}

export async function activateApiVehicle(baseUrl: string, vehicleId: string) {
  await request<ApiVehicleProfile>(baseUrl, `/api/v1/vehicles/${encodeURIComponent(vehicleId)}/active`, {
    method: "PUT",
  });
}

export async function deleteApiVehicle(baseUrl: string, vehicleId: string) {
  await request<void>(baseUrl, `/api/v1/vehicles/${encodeURIComponent(vehicleId)}`, {
    method: "DELETE",
  });
}
