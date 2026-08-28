import { getVehicleManual } from "./manual";

describe("approved catalog manual metadata", () => {
  it("uses the exact persisted KGM source without inventing an image", () => {
    const manual = getVehicleManual({
      id: "kgm-test",
      nickname: "테스트 차량",
      manufacturer: "KGM",
      model: "테스트 SUV",
      modelYear: 2025,
      powertrain: "gasoline",
      fuelGrade: "regular",
      manual: {
        siteId: "kgm",
        modelName: "테스트 SUV",
        generation: "T1",
        modelYear: 2025,
        title: "테스트 SUV 취급설명서",
        sourceUrl: "https://www.kg-mobility.com/manual/test",
        verifiedAt: "2026-08-28",
      },
    });

    expect(manual).toMatchObject({
      siteId: "kgm",
      generation: "T1",
      manualTitle: "테스트 SUV 취급설명서",
      manualUrl: "https://www.kg-mobility.com/manual/test",
    });
    expect(manual?.imageUrl).toBeUndefined();
  });
});
