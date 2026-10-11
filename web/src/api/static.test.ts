import { describe, expect, it } from "vitest";
import { snapConditions } from "../lib/conditions";
import { nearestIndex, staticPath } from "./static";

// The exporter's grid (api/src/hclust_api/export.py): 298.15 K is index 12, 1 atm index 6.
const grid = {
  temperatures: [10, 13.5, 18.2, 24.6, 33.2, 44.9, 60.6, 81.8, 110, 149, 201, 272, 298.15, 367, 495, 669, 903, 1220, 1650, 2220, 3000],
  pressures: [1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 0.1, 1, 10, 100, 1000],
  default: [12, 6] as [number, number],
};
const at = (path: string) => staticPath(new URL(path, "https://example.org"), grid);

describe("static file for an API request", () => {
  // the same examples as api/tests/test_export.py: the two sides must agree
  it("folds the query into the path, conditions first", () => {
    expect(at("/api/campaigns")).toBe("campaigns.json");
    expect(at("/api/campaigns/baseline/grid?temperature=298.15&pressure=1&quantity=d_g"))
      .toBe("campaigns/baseline/grid/c12-6,quantity-d_g.json");
    expect(at("/api/campaigns/baseline/states/5/1/1?temperature=10&pressure=1000"))
      .toBe("campaigns/baseline/states/5/1/1/c0-9.json");
    expect(at("/api/campaigns/baseline/benchmark?test=L1M")).toBe("campaigns/baseline/benchmark/test-L1M.json");
    expect(at("/api/structures/3094.xyz")).toBe("structures/3094.xyz");
  });
  it("snaps any temperature and pressure to the nearest exported one (log scale)", () => {
    expect(at("/api/campaigns/baseline/grid?quantity=d_e&pressure=0.7&temperature=300"))
      .toBe("campaigns/baseline/grid/c12-6,quantity-d_e.json");
    expect(nearestIndex(grid.pressures, 3e-6)).toBe(0); // log midpoint of 1e-6 and 1e-5 is 3.16e-6
    expect(nearestIndex(grid.pressures, 4e-6)).toBe(1);
  });
  it("rejects non-API paths", () => {
    expect(() => at("/data/manifest.json")).toThrow();
  });
});

describe("conditions on the static site", () => {
  it("show the exported values they snap to", () => {
    expect(snapConditions({ temperature: 300, pressure: 0.7 }, grid)).toEqual({ temperature: 298.15, pressure: 1 });
    expect(snapConditions({ temperature: 300, pressure: 0.7 }, undefined)).toEqual({ temperature: 300, pressure: 0.7 });
  });
});
