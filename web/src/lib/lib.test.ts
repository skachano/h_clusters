import { describe, expect, it, vi } from "vitest";
import { niceExtent, ticks } from "../components/charts/frame";
import { atomLabel, atomSummaries } from "./atoms";
import { pretty, signed, species } from "./format";
import { bondStyle, bonds, parseXyz, project, setBonds } from "./geometry";
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

describe("3D viewer bonds", () => {
  it("bonds H2+ at 1.06 Å, which 3Dmol's own guess leaves out", () => {
    const atoms = [{}, {}, {}] as { index?: number; bonds?: number[]; bondOrder?: number[] }[];
    setBonds(atoms, "3\n\nH 0 0 0\nH 0 0 1.058\nH 0 0 3.2\n");
    expect(atoms.map((a) => a.bonds)).toEqual([[1], [0], []]);
    expect(atoms[0].bondOrder).toEqual([1]);
    expect(atoms.map((a) => a.index)).toEqual([0, 1, 2]); // 3Dmol draws a bond from the lower index
  });
});

describe("bond-order styling", () => {
  it("thickens and darkens with the order and drops van der Waals contacts", () => {
    expect(bondStyle(0.01)).toBeNull();
    const [link, h2] = [bondStyle(0.25)!, bondStyle(1)!];
    expect(link.radius).toBeLessThan(h2.radius);
    expect(link.opacity).toBeLessThan(h2.opacity);
    expect(h2.radius).toBeCloseTo(0.11, 9);
    expect(h2.opacity).toBe(1);
    expect(bondStyle(1.2)).toEqual(h2);
    expect(bondStyle(0.03)!.opacity).toBeGreaterThanOrEqual(0.2);
  });
});

describe("atom summaries", () => {
  const bonds = {
    structure_id: 1, method: "m", mayer: [],
    loewdin: [{ i: 0, j: 1, order: 0.99 }, { i: 1, j: 2, order: 0.02 }],
    atoms: [
      { charge: 0.003, spin: 0.001, valence: 1, free_valence: 0 },
      { charge: -0.009, spin: 0.009, valence: 1, free_valence: 0 },
      { charge: 0.006, spin: 0.99, valence: 1, free_valence: 0.99 },
    ],
  };
  it("sums each atom's bond orders and names atoms like the bond table", () => {
    const a = atomSummaries(bonds);
    expect(a.map((x) => x.name)).toEqual(["H1", "H2", "H3"]);
    expect(a[1].bondSum).toBeCloseTo(1.01, 9);
  });
  it("labels the radical atom with its spin and free valence", () => {
    const [h1, , h3] = atomSummaries(bonds);
    expect(atomLabel(h3)).toBe("H3: charge +0.01, spin +0.99, Σ bond order 0.02, free valence 0.99");
    expect(atomLabel(h1)).not.toContain("free valence");
    const closed = atomSummaries({ ...bonds, atoms: bonds.atoms.map((x) => ({ ...x, spin: null })) });
    expect(atomLabel(closed[0])).toBe("H1: charge +0.00, Σ bond order 0.99");
  });
});

describe("viewer zoom", () => {
  it("zooms in on clusters smaller than 3Dmol's 5 Å box, never out", async () => {
    vi.mock("3dmol", () => ({}));
    const { smallZoom } = await import("../components/MoleculeViewer");
    expect(smallZoom("2\n\nH 0 0 0\nH 0 0 0.74\n")).toBeCloseTo(5 / 1.34, 6);
    expect(smallZoom("1\n\nH 0 0 0\n")).toBe(4);
    expect(smallZoom("2\n\nH 0 0 0\nH 0 0 9\n")).toBe(1);
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
