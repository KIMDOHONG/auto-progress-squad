import { parseVehicleRegistration } from "./officialVehicle";

describe("official vehicle input parsing", () => {
  it("extracts a year and model when the manufacturer is omitted", () => {
    expect(parseVehicleRegistration("2020 K5 등록해줘")).toEqual({
      manufacturer: undefined,
      manufacturerSupport: "unspecified",
      modelQuery: "K5",
      modelYear: 2020,
    });
  });

  it("normalizes a Genesis model alias", () => {
    expect(parseVehicleRegistration("제네시스 2027 egv70 추가")).toEqual({
      manufacturer: "제네시스",
      manufacturerSupport: "connected",
      modelQuery: "ELECTRIFIED GV70",
      modelYear: 2027,
    });
  });

  it("recognizes manufacturers whose official page is link-only", () => {
    expect(parseVehicleRegistration("2018 쉐보레 말리부 등록")).toMatchObject({
      manufacturer: "쉐보레",
      manufacturerSupport: "official-link",
      manufacturerManualUrl: "https://www.chevrolet.co.kr/owner-manuals",
      modelQuery: "말리부",
      modelYear: 2018,
    });
  });

  it("does not claim that an unconnected manufacturer was searched", () => {
    expect(parseVehicleRegistration("2015 BMW M3 등록")).toMatchObject({
      manufacturer: "BMW",
      manufacturerSupport: "unsupported",
      modelQuery: "M3",
      modelYear: 2015,
    });
  });

  it("requires a four digit model year", () => {
    expect(parseVehicleRegistration("K5 등록")).toBeNull();
  });
});
