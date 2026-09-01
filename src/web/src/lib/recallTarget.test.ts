import { DEFAULT_VEHICLES } from "./vehicle";
import { resolveRecallTarget } from "./recallTarget";
import type { VehicleProfile } from "../types";

const activeVehicle = DEFAULT_VEHICLES[0];

describe("resolveRecallTarget", () => {
  it.each(["리콜", "리콜 조회", "내 차 리콜 확인해줘", "현재 차량 리콜 있어?"])(
    "uses the active vehicle for a generic recall request: %s",
    (query) => {
      expect(resolveRecallTarget(query, DEFAULT_VEHICLES, activeVehicle)).toEqual({
        kind: "active",
        vehicle: activeVehicle,
      });
    },
  );

  it("uses a registered vehicle explicitly named in the request instead of the active vehicle", () => {
    expect(resolveRecallTarget("2021 BMW M3 리콜 확인", DEFAULT_VEHICLES, activeVehicle)).toEqual({
      kind: "explicit",
      vehicle: DEFAULT_VEHICLES[2],
    });
  });

  it("matches a registered vehicle nickname", () => {
    expect(resolveRecallTarget("주말 차량 리콜 알려줘", DEFAULT_VEHICLES, activeVehicle)).toEqual({
      kind: "explicit",
      vehicle: DEFAULT_VEHICLES[2],
    });
  });

  it("does not silently fall back to the active vehicle for an unregistered explicit vehicle", () => {
    expect(resolveRecallTarget("2025 K5 리콜", DEFAULT_VEHICLES, activeVehicle)).toEqual({
      kind: "missing",
      query: "2025 K5",
    });
  });

  it("requires clarification when the named model matches multiple registered years", () => {
    const vehicles: VehicleProfile[] = [
      { id: "k5-2020", nickname: "구형 K5", manufacturer: "기아", model: "K5", modelYear: 2020, powertrain: "gasoline" },
      { id: "k5-2025", nickname: "신형 K5", manufacturer: "기아", model: "K5", modelYear: 2025, powertrain: "gasoline" },
    ];

    expect(resolveRecallTarget("K5 리콜", vehicles, vehicles[1])).toEqual({
      kind: "ambiguous",
      vehicles,
    });
    expect(resolveRecallTarget("2025 K5 리콜", vehicles, vehicles[0])).toEqual({
      kind: "explicit",
      vehicle: vehicles[1],
    });
  });
});
