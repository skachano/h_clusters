// XYZ parsing and a 2D projection for the shape thumbnails in the grid.

export interface Atom {
  symbol: string;
  x: number;
  y: number;
  z: number;
}

export function parseXyz(xyz: string): Atom[] {
  const lines = xyz.trim().split("\n");
  const n = Number(lines[0]);
  return lines.slice(2, 2 + n).map((line) => {
    const [symbol, x, y, z] = line.trim().split(/\s+/);
    return { symbol, x: Number(x), y: Number(y), z: Number(z) };
  });
}

export const BOND_CUTOFF = 1.15; // Å, as hclust.structures.BOND_CUTOFF

/**
 * Rotate so the largest spread lies along x and the next along y (principal axes of the
 * point cloud), then drop z: the view that shows most of the shape.
 */
export function project(atoms: Atom[]): { x: number; y: number; depth: number }[] {
  const { center, axes } = principalFrame(atoms);
  return atoms.map((a) => {
    const v = [a.x - center[0], a.y - center[1], a.z - center[2]];
    return { x: dot(v, axes[0]), y: dot(v, axes[1]), depth: dot(v, axes[2]) };
  });
}

/** Centre and principal axes (largest spread first) of the atoms' positions. */
export function principalFrame(atoms: Atom[]): { center: number[]; axes: [number[], number[], number[]] } {
  const n = Math.max(1, atoms.length);
  const center = [0, 1, 2].map((k) => atoms.reduce((s, a) => s + [a.x, a.y, a.z][k], 0) / n);
  const p = atoms.map((a) => [a.x - center[0], a.y - center[1], a.z - center[2]]);
  const cov = [0, 1, 2].map((i) => [0, 1, 2].map((j) => p.reduce((s, v) => s + v[i] * v[j], 0)));
  const [e1, e2] = topEigenvectors(cov);
  return { center, axes: [e1, e2, cross(e1, e2)] };
}

/** Express a vector in a frame's axes. */
export const inFrame = (v: number[], axes: number[][]) => axes.map((e) => dot(v, e));

export function bonds(atoms: Atom[], cutoff = BOND_CUTOFF): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i < atoms.length; i++)
    for (let j = i + 1; j < atoms.length; j++) {
      const d = Math.hypot(atoms[i].x - atoms[j].x, atoms[i].y - atoms[j].y, atoms[i].z - atoms[j].z);
      if (d < cutoff) out.push([i, j]);
    }
  return out;
}

const dot = (a: number[], b: number[]) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a: number[], b: number[]) => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
const norm = (a: number[]) => {
  const l = Math.hypot(a[0], a[1], a[2]) || 1;
  return a.map((x) => x / l);
};
const mul = (m: number[][], v: number[]) => m.map((row) => dot(row, v));

/** The two leading eigenvectors of a symmetric 3×3 matrix, by power iteration + deflation. */
function topEigenvectors(m: number[][]): [number[], number[]] {
  const power = (mat: number[][], start: number[]) => {
    let v = norm(start);
    for (let i = 0; i < 100; i++) v = norm(mul(mat, v));
    return v;
  };
  const v1 = Math.hypot(...m.flat()) < 1e-12 ? [1, 0, 0] : power(m, [1, 0.31, 0.17]);
  const lambda = dot(v1, mul(m, v1));
  const deflated = m.map((row, i) => row.map((x, j) => x - lambda * v1[i] * v1[j]));
  let v2 = power(deflated, cross(v1, [0.13, 0.71, 0.29]));
  v2 = norm(v2.map((x, i) => x - dot(v2, v1) * v1[i])); // keep it orthogonal
  if (!Number.isFinite(v2[0]) || Math.hypot(...v2) < 0.5) v2 = norm(cross(v1, Math.abs(v1[2]) < 0.9 ? [0, 0, 1] : [0, 1, 0]));
  return [v1, v2];
}

/**
 * Bonds for the 3D viewer from our own rule (d < BOND_CUTOFF, as the thumbnails and the
 * composition labels), not 3Dmol's guess: that one only bonds H-H between 0.71 and 0.99 Å, so
 * it drops the 1.04-1.06 Å bond of H2+ and of the H2+ core in H6+, H8+, H10+. Atoms keep the
 * order of the XYZ. 3Dmol fills `index` only when it guesses bonds itself, and draws a bond
 * only from the lower index, so it is set here too.
 */
export function setBonds(atoms: { index?: number; bonds?: number[]; bondOrder?: number[] }[], xyz: string) {
  for (const [i, a] of atoms.entries()) {
    a.index = i;
    a.bonds = [];
    a.bondOrder = [];
  }
  for (const [i, j] of bonds(parseXyz(xyz))) {
    atoms[i].bonds!.push(j);
    atoms[i].bondOrder!.push(1);
    atoms[j].bonds!.push(i);
    atoms[j].bondOrder!.push(1);
  }
}

/** Bond orders below this are not drawn (van der Waals contacts are ~0.01). */
export const MIN_BOND_ORDER = 0.03;
const MAX_OPACITY = 0.75; // a full bond stays see-through
const OPACITY_GROWTH = 3; // e-folds of opacity over orders 0 -> 1

/**
 * Cylinder for a bond order: radius grows with sqrt(order), so 0.1-0.3 links stay visible
 * next to a full H2 bond; opacity grows exponentially, (e^(k·order) - 1) / (e^k - 1), so weak
 * links are almost transparent (order 0.3: 6 %, 0.5: 14 %) while strong bonds stand out, up
 * to a ceiling below 1 so even a full bond never hides the bonds behind it.
 * Orders above 1 are drawn as 1.
 */
export function bondStyle(order: number): { radius: number; opacity: number } | null {
  if (order < MIN_BOND_ORDER) return null;
  const o = Math.min(order, 1);
  const k = OPACITY_GROWTH;
  return { radius: 0.025 + 0.085 * Math.sqrt(o), opacity: MAX_OPACITY * Math.expm1(k * o) / Math.expm1(k) };
}

