export type Powertrain = "electric" | "hydrogen" | "gasoline" | "diesel" | "hybrid";

export type FuelGrade = "regular" | "premium" | "super-premium" | "diesel" | "high-cetane";

export interface VehicleProfile {
  id: string;
  nickname: string;
  manufacturer: string;
  model: string;
  modelYear: number;
  powertrain: Powertrain;
  fuelGrade?: FuelGrade;
  batteryCapacityKwh?: number;
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
