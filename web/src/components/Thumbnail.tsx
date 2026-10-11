// A small 2D drawing of a structure: atoms projected on their principal plane, bonds < 1.15 Å.
import { useMemo } from "react";
import { bonds, parseXyz, project } from "../lib/geometry";

export function Thumbnail({ xyz, size = 56, ink = "currentColor" }: { xyz: string; size?: number; ink?: string }) {
  const drawing = useMemo(() => {
    const atoms = parseXyz(xyz);
    const p = project(atoms);
    const extent = Math.max(0.6, ...p.map((q) => Math.max(Math.abs(q.x), Math.abs(q.y))));
    const pad = 7;
    const scale = (size / 2 - pad) / extent;
    const pts = p.map((q) => ({ x: size / 2 + q.x * scale, y: size / 2 - q.y * scale, depth: q.depth }));
    const order = pts.map((_, i) => i).sort((a, b) => pts[a].depth - pts[b].depth);
    const dmax = Math.max(1e-6, ...pts.map((q) => Math.abs(q.depth)));
    return { pts, order, dmax, bonds: bonds(atoms), scale };
  }, [xyz, size]);
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
