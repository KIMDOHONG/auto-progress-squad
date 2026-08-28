export type Powertrain = "electric" | "hydrogen" | "gasoline" | "diesel" | "hybrid";

export type FuelGrade = "regular" | "premium" | "super-premium" | "diesel" | "high-cetane";

export type OfficialManualSiteId = "hmc" | "kia" | "genesis";

export interface OfficialManualMetadata {
  siteId: OfficialManualSiteId;
  modelName: string;
  projectCode: string;
  modelYear: number;
  imageUrl: string;
  verifiedAt: string;
}

export type ManualIngestionState = "unavailable" | "pending" | "ready" | "failed";

export interface ManualIngestionStatus {
  vehicleId: string;
  status: ManualIngestionState;
  documentKey?: string;
  sourceUrl?: string;
  attemptCount: number;
  failureCode?: string;
  failureMessage?: string;
  queuedAt?: string;
  updatedAt?: string;
  readyAt?: string;
  canSearch: boolean;
}

export interface ManualSearchSource {
  documentName: string;
  sourceUrl: string;
  page?: number;
  section?: string;
  excerpt: string;
}

export interface ManualSearchResult {
  answer: string;
  sources: ManualSearchSource[];
  generatedAt: string;
}

export interface VehicleProfile {
  id: string;
  nickname: string;
  manufacturer: string;
  model: string;
  modelYear: number;
  powertrain: Powertrain;
  fuelGrade?: FuelGrade;
  batteryCapacityKwh?: number;
  manual?: OfficialManualMetadata;
}

export type AppView = "dashboard" | "maintenance" | "manual" | "planner" | "used-car";

export interface VehicleDraft {
  nickname: string;
  manufacturer: string;
  model: string;
  modelYear: string;
  powertrain: Powertrain;
  fuelGrade: FuelGrade;
  batteryCapacityKwh: string;
}
