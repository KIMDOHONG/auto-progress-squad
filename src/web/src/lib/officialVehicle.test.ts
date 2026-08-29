import { parseVehicleRegistration, searchOfficialVehicles } from "./officialVehicle";

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

  it("searches only connected manufacturers when the manufacturer is omitted", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("ownersmanual.kia.com") && url.includes("/models")) {
        return { ok: true, status: 200, json: async () => ({ CARS: [{ langModelName: "K5" }] }) } as Response;
      }
      if (url.includes("ownersmanual.kia.com") && url.includes("/model?")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            years: ["2025"],
            yearModels: {
              "2025": [
                { modelName: "K5", projCode: "DL3", year: "2025", fuel: "ICE", mainImgUrl: "/api/v2/kia/files/2270/DLSD24SWP.png" },
              ],
            },
          }),
        } as Response;
      }
      if (url.includes("ownersmanual.hyundai.com") || url.includes("ownersmanual.genesis.com")) {
        return { ok: true, status: 200, json: async () => ({ CARS: [] }) } as Response;
      }
      throw new Error(`unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const request = parseVehicleRegistration("2025 K5 등록");
    expect(request).not.toBeNull();
    const result = await searchOfficialVehicles(request!);

    expect(result.candidates).toHaveLength(1);
    expect(result.candidates[0]).toMatchObject({
      manufacturer: "기아",
      modelName: "K5",
      modelYear: 2025,
      projectCode: "DL3",
    });
    const requestedUrls = fetchMock.mock.calls.map(([input]) => String(input));
    expect(requestedUrls.some((url) => url.includes("chevrolet.co.kr"))).toBe(false);
    expect(requestedUrls.some((url) => url.includes("kg-mobility.com"))).toBe(false);
    vi.unstubAllGlobals();
  });
});
