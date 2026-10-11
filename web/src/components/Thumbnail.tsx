// A small 2D drawing of a structure: atoms projected on their principal plane, bonds with a
// Löwdin bond order above 0.33 (from the API), or H-H < 1.15 Å for structures without bond orders.
import { useMemo } from "react";
import { bonds as byDistance, parseXyz, project } from "../lib/geometry";

export function Thumbnail({ xyz, bonds, size = 56, ink = "currentColor" }: {
  xyz: string; bonds?: [number, number][] | null; size?: number; ink?: string;
}) {
  const drawing = useMemo(() => {
    const atoms = parseXyz(xyz);
    const p = project(atoms);
    const extent = Math.max(0.6, ...p.map((q) => Math.max(Math.abs(q.x), Math.abs(q.y))));
    const pad = 7;
    const scale = (size / 2 - pad) / extent;
    const pts = p.map((q) => ({ x: size / 2 + q.x * scale, y: size / 2 - q.y * scale, depth: q.depth }));
    const order = pts.map((_, i) => i).sort((a, b) => pts[a].depth - pts[b].depth);
    const dmax = Math.max(1e-6, ...pts.map((q) => Math.abs(q.depth)));
    return { pts, order, dmax, bonds: bonds ?? byDistance(atoms), scale };
  }, [xyz, bonds, size]);
  const r = Math.max(2.2, Math.min(4.5, drawing.scale * 0.22));
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
      {drawing.bonds.map(([i, j]) => (
        <line
          key={`${i}-${j}`}
          x1={drawing.pts[i].x} y1={drawing.pts[i].y} x2={drawing.pts[j].x} y2={drawing.pts[j].y}
          stroke={ink} strokeWidth={1.6} strokeLinecap="round" opacity={0.75}
        />
      ))}
      {drawing.order.map((i) => {
        const q = drawing.pts[i];
        // nearer atoms (larger depth) are drawn later and fuller
        const near = 0.55 + 0.45 * ((q.depth / drawing.dmax + 1) / 2);
        return <circle key={i} cx={q.x} cy={q.y} r={r} fill={ink} opacity={near} />;
      })}
    </svg>
  );
}
