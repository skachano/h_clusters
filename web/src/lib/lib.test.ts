import { describe, expect, it } from "vitest";
import { niceExtent, ticks } from "../components/charts/frame";
import { pretty, signed, species } from "./format";
import { bonds, parseXyz, project } from "./geometry";
import { valueStep } from "./scales";

describe("format", () => {
  it("writes species with sub- and superscripts", () => {
    expect(pretty("H3+ (1)")).toBe("H₃⁺ (1)");
    expect(pretty("H10-")).toBe("H₁₀⁻");
    expect(pretty("H2(3) + e-")).toBe("H₂(3) + e⁻");
    expect(species(1, -1)).toBe("H⁻");
    expect(species(2, 0)).toBe("H₂");
  });
  it("signs numbers with a true minus", () => {
    expect(signed(0.25, 2)).toBe("+0.25");
    expect(signed(-1.5, 1, "eV")).toBe("−1.5 eV");
    expect(signed(null)).toBe("–");
  });
});

describe("diverging bins", () => {
  it("is neutral near zero and signed by arm", () => {
    expect(valueStep(0.005).bin).toBe(0);
    expect(valueStep(0.02)).toMatchObject({ bin: 1, fill: "var(--div-pos-1)" });
    expect(valueStep(-0.5)).toMatchObject({ bin: -3, fill: "var(--div-neg-3)" });
    expect(valueStep(4.7).bin).toBe(4);
    expect(valueStep(null).fill).toBe("var(--none)");
  });
});

describe("geometry", () => {
  const triangle = "3\n\nH 0 0 0\nH 0.87 0 0\nH 0.435 0.753 0\n";
  it("finds bonds below 1.15 Å", () => {
    expect(bonds(parseXyz(triangle))).toHaveLength(3);
    expect(bonds(parseXyz("2\n\nH 0 0 0\nH 0 0 3\n"))).toHaveLength(0);
  });
  it("projects onto the plane of a planar molecule", () => {
    const p = project(parseXyz(triangle.replace(/ 0\n/g, " 0\n")));
    expect(Math.max(...p.map((q) => Math.abs(q.depth)))).toBeLessThan(1e-9);
    // distances are preserved in the plane
    expect(Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y)).toBeCloseTo(0.87, 6);
  });
});

describe("chart frame", () => {
  it("makes round ticks", () => {
    expect(ticks(0, 4.7, 5)).toEqual([0, 1, 2, 3, 4]);
    expect(ticks(-2.5, 0.5, 4)).toEqual([-2, -1, 0]); // step 1: the first round step >= 0.75
  });
  it("pads an extent to ticks and includes zero", () => {
    expect(niceExtent([0.3, 4.6], 0)).toEqual([0, 5]);
    expect(niceExtent([-2.45, -2.3], 0, 4)).toEqual([-3, 0]);
  });
});
