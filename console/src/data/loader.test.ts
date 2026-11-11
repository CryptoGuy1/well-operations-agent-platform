import { mockFetch } from "../test/fixtures";
import { BundleError, bundleUrl, loadJson } from "./loader";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("bundleUrl", () => {
  it("resolves a bundle file against the page base", () => {
    expect(bundleUrl("evaluation/r2.json", "./")).toBe("./data/evaluation/r2.json");
    expect(bundleUrl("wells.json", "/console")).toBe("/console/data/wells.json");
  });

  it("refuses paths outside the bundle", () => {
    expect(() => bundleUrl("/etc/x.json")).toThrow(BundleError);
    expect(() => bundleUrl("../secret.json")).toThrow(BundleError);
  });
});

describe("loadJson", () => {
  it("fetches each file once", async () => {
    const fetchMock = mockFetch({ "wells.json": [{ key: "9001" }] });
    const first = await loadJson("wells.json");
    const second = await loadJson("wells.json");
    expect(first).toEqual([{ key: "9001" }]);
    expect(second).toBe(first);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("rejects a missing file and does not cache the failure", async () => {
    const fetchMock = mockFetch({});
    await expect(loadJson("wells.json")).rejects.toThrow("wells.json: HTTP 404");
    await expect(loadJson("wells.json")).rejects.toBeInstanceOf(BundleError);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("rejects content that fails the check", async () => {
    mockFetch({ "evaluation/r2.json": { nope: true } });
    const isList = (v: unknown): v is unknown[] => Array.isArray(v);
    await expect(loadJson("evaluation/r2.json", isList)).rejects.toThrow("unexpected content");
  });
});
