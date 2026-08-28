import type { CatalogManualAdapterId, ManualIngestionStatus, ManualSearchResult, OfficialManualSiteId, VehicleProfile } from "../types";

interface ApiVehicleProfile {
  id: string;
  nickname: string;
  manufacturer: string;
  model: string;
  model_year: number;
  powertrain: VehicleProfile["powertrain"];
  fuel_grade: VehicleProfile["fuelGrade"] | null;
  battery_capacity_kwh: number | null;
  manual_site_id: OfficialManualSiteId | null;
  manual_model_name: string | null;
  manual_project_code: string | null;
  manual_generation: string | null;
  manual_model_year: number | null;
  manual_image_url: string | null;
  manual_title: string | null;
  manual_source_url: string | null;
  manual_verified_at: string | null;
  is_active: boolean;
}

interface ApiVehicleList {
  items: ApiVehicleProfile[];
  active_vehicle_id: string | null;
}

interface ApiErrorPayload {
  error?: { code?: string; message?: string };
}

interface ApiManualIngestionStatus {
  vehicle_id: string;
  status: ManualIngestionStatus["status"];
  document_key: string | null;
  source_url: string | null;
  attempt_count: number;
  failure_code: string | null;
  failure_message: string | null;
  queued_at: string | null;
  updated_at: string | null;
  ready_at: string | null;
  can_search: boolean;
}

interface ApiManualSearchResult {
  answer: string;
  sources: Array<{
    document_name: string;
    source_url: string;
    page: number | null;
    section: string | null;
    excerpt: string;
  }>;
  generated_at: string;
}

export class VehicleApiError extends Error {
  constructor(public readonly code: string, message: string) {
    super(message);
  }
}

function fromApi(vehicle: ApiVehicleProfile): VehicleProfile {
  const manual = vehicle.manual_site_id
    && vehicle.manual_model_name
    && vehicle.manual_model_year
    && vehicle.manual_verified_at
    ? {
        siteId: vehicle.manual_site_id,
        modelName: vehicle.manual_model_name,
        modelYear: vehicle.manual_model_year,
        verifiedAt: vehicle.manual_verified_at,
        ...(vehicle.manual_project_code ? { projectCode: vehicle.manual_project_code } : {}),
        ...(vehicle.manual_generation ? { generation: vehicle.manual_generation } : {}),
        ...(vehicle.manual_image_url ? { imageUrl: vehicle.manual_image_url } : {}),
        ...(vehicle.manual_title ? { title: vehicle.manual_title } : {}),
        ...(vehicle.manual_source_url ? { sourceUrl: vehicle.manual_source_url } : {}),
      }
    : undefined;
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
    ...(manual ? { manual } : {}),
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
    manual_site_id: vehicle.manual?.siteId ?? null,
    manual_model_name: vehicle.manual?.modelName ?? null,
    manual_project_code: vehicle.manual?.projectCode ?? null,
    manual_generation: vehicle.manual?.generation ?? null,
    manual_model_year: vehicle.manual?.modelYear ?? null,
    manual_image_url: vehicle.manual?.imageUrl ?? null,
    manual_title: vehicle.manual?.title ?? null,
    manual_source_url: vehicle.manual?.sourceUrl ?? null,
    manual_verified_at: vehicle.manual?.verifiedAt ?? null,
  };
}

function ingestionFromApi(value: ApiManualIngestionStatus): ManualIngestionStatus {
  return {
    vehicleId: value.vehicle_id,
    status: value.status,
    attemptCount: value.attempt_count,
    canSearch: value.can_search,
    ...(value.document_key ? { documentKey: value.document_key } : {}),
    ...(value.source_url ? { sourceUrl: value.source_url } : {}),
    ...(value.failure_code ? { failureCode: value.failure_code } : {}),
    ...(value.failure_message ? { failureMessage: value.failure_message } : {}),
    ...(value.queued_at ? { queuedAt: value.queued_at } : {}),
    ...(value.updated_at ? { updatedAt: value.updated_at } : {}),
    ...(value.ready_at ? { readyAt: value.ready_at } : {}),
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

export async function attachApiManualAdapter(
  baseUrl: string,
  vehicleId: string,
  adapterId: CatalogManualAdapterId,
  generation?: string,
) {
  const response = await request<ApiVehicleProfile>(
    baseUrl,
    `/api/v1/vehicles/${encodeURIComponent(vehicleId)}/manual-adapters/${adapterId}`,
    {
      method: "POST",
      body: JSON.stringify({ generation: generation ?? null }),
    },
  );
  return fromApi(response);
}

export async function getApiManualIngestion(baseUrl: string, vehicleId: string) {
  const response = await request<ApiManualIngestionStatus>(
    baseUrl,
    `/api/v1/vehicles/${encodeURIComponent(vehicleId)}/manual-ingestion`,
  );
  return ingestionFromApi(response);
}

export async function retryApiManualIngestion(baseUrl: string, vehicleId: string) {
  const response = await request<ApiManualIngestionStatus>(
    baseUrl,
    `/api/v1/vehicles/${encodeURIComponent(vehicleId)}/manual-ingestion/retry`,
    { method: "POST" },
  );
  return ingestionFromApi(response);
}

export async function searchApiManual(
  baseUrl: string,
  vehicleId: string,
  question: string,
): Promise<ManualSearchResult> {
  const response = await request<ApiManualSearchResult>(baseUrl, "/api/v1/manual/search", {
    method: "POST",
    body: JSON.stringify({ vehicle_id: vehicleId, question, limit: 5 }),
  });
  return {
    answer: response.answer,
    generatedAt: response.generated_at,
    sources: response.sources.map((source) => ({
      documentName: source.document_name,
      sourceUrl: source.source_url,
      excerpt: source.excerpt,
      ...(source.page ? { page: source.page } : {}),
      ...(source.section ? { section: source.section } : {}),
    })),
  };
}
