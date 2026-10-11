// Lines against an integer x (cluster size m): 2px lines, ringed end dots, crosshair tooltip
// listing every series at the hovered x, legend + direct end labels (≤ 3 series).
import { useMemo, useRef, useState } from "react";
import { useTooltip } from "../Tooltip";
import { linear, niceExtent, tickLabel, ticks, useWidth } from "./frame";

export type Marker = "ring" | "dot" | "square";

export interface Series {
  key: string;
  label: string;
  color: string;
  /** Second encoding besides colour; also keeps coinciding points of two series visible. */
  marker?: Marker;
  points: { x: number; y: number | null; note?: string | null }[];
}

function MarkerShape({ kind = "dot", x, y, r, color }: { kind?: Marker; x: number; y: number; r: number; color: string }) {
  if (kind === "ring")
    return <circle cx={x} cy={y} r={r + 2} fill="none" stroke={color} strokeWidth={2} />;
  if (kind === "square")
    return <rect x={x - r} y={y - r} width={2 * r} height={2 * r} rx={1} fill={color} stroke="var(--surface-1)" strokeWidth={2} />;
  return <circle cx={x} cy={y} r={r} fill={color} stroke="var(--surface-1)" strokeWidth={2} />;
}

export function MarkerKey({ kind = "dot", color }: { kind?: Marker; color: string }) {
  return (
    <svg width={22} height={12} aria-hidden="true">
      <line x1={0} x2={22} y1={6} y2={6} stroke={color} strokeWidth={2} />
      <MarkerShape kind={kind} x={11} y={6} r={3.5} color={color} />
    </svg>
  );
}

export function LineChart({ series, xLabel, yLabel, unit, height = 320, zeroLine = true, format }: {
  series: Series[]; xLabel: string; yLabel: string; unit: string; height?: number; zeroLine?: boolean;
  format: (v: number | null) => string;
}) {
  const ref = useRef<SVGSVGElement>(null);
  const [box, width] = useWidth<HTMLDivElement>();
  const [hoverX, setHoverX] = useState<number | null>(null);
  const tip = useTooltip();
  const m = { top: 16, right: 84, bottom: 44, left: 60 };

  const { x, y, xs, yTicks } = useMemo(() => {
    const allX = series.flatMap((s) => s.points.map((p) => p.x));
    const allY = series.flatMap((s) => s.points.flatMap((p) => (p.y == null ? [] : [p.y])));
    const xs = [...new Set(allX)].sort((a, b) => a - b);
    const yDomain = niceExtent(allY, zeroLine ? 0 : undefined);
    return {
      xs,
      x: linear([Math.min(...xs), Math.max(...xs)], [m.left, width - m.right]),
      y: linear(yDomain, [height - m.bottom, m.top]),
      yTicks: ticks(yDomain[0], yDomain[1], 5),
    };
  }, [series, height, zeroLine, width, m.left, m.right, m.bottom, m.top]);

  const path = (s: Series) => {
    let d = "";
    let pen = false;
    for (const p of s.points) {
      if (p.y == null) {
        pen = false;
        continue;
      }
      d += `${pen ? "L" : "M"}${x(p.x).toFixed(1)},${y(p.y).toFixed(1)}`;
      pen = true;
    }
    return d;
  };

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const svg = ref.current;
    if (!svg) return;
    const box = svg.getBoundingClientRect();
    const px = ((e.clientX - box.left) / box.width) * width;
    const nearest = xs.reduce((best, v) => (Math.abs(x(v) - px) < Math.abs(x(best) - px) ? v : best), xs[0]);
    setHoverX(nearest);
    tip.show(e.clientX, e.clientY, (
      <div>
        <div className="tt-label">{xLabel} = {nearest}</div>
        {series.map((s) => {
          const p = s.points.find((q) => q.x === nearest);
          return (
            <div className="tt-row" key={s.key}>
              <MarkerKey kind={s.marker} color={s.color} />
              <span className="tt-value">{format(p?.y ?? null)}</span>
              <span className="tt-label">{s.label}{p?.note ? ` · ${p.note}` : ""}</span>
            </div>
          );
        })}
      </div>
    ));
  };

  // Direct end labels: at each series' last point, nudged apart only if they collide.
  const ends = series
    .map((s) => {
      const last = [...s.points].reverse().find((p) => p.y != null);
      return last ? { s, y: y(last.y as number), x: x(last.x) } : null;
    })
    .filter((v): v is { s: Series; y: number; x: number } => v !== null)
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 14) ends[i].y = ends[i - 1].y + 14;

  return (
    <div ref={box}>
      <div className="legend" style={{ marginBottom: 8 }}>
        {series.map((s) => (
          <span className="legend-item" key={s.key}>
            <MarkerKey kind={s.marker} color={s.color} />
            {s.label}
          </span>
        ))}
      </div>
      <svg
        ref={ref} viewBox={`0 0 ${width} ${height}`} width="100%" role="img"
        aria-label={`${yLabel} against ${xLabel}`}
        onPointerMove={onMove} onPointerLeave={() => { setHoverX(null); tip.hide(); }}
        style={{ display: "block", touchAction: "none" }}
      >
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={m.left} x2={width - m.right} y1={y(t)} y2={y(t)} stroke={t === 0 && zeroLine ? "var(--axis)" : "var(--grid)"} strokeWidth={1} />
            <text x={m.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} fill="var(--text-muted)" className="num">{tickLabel(t)}</text>
          </g>
        ))}
        {xs.map((v) => (
          <text key={v} x={x(v)} y={height - m.bottom + 18} textAnchor="middle" fontSize={11} fill="var(--text-muted)" className="num">{v}</text>
        ))}
        <text x={(m.left + width - m.right) / 2} y={height - 6} textAnchor="middle" fontSize={12} fill="var(--text-secondary)">{xLabel}</text>
        <text transform={`translate(14 ${(m.top + height - m.bottom) / 2}) rotate(-90)`} textAnchor="middle" fontSize={12} fill="var(--text-secondary)">{yLabel} ({unit})</text>
        {hoverX != null && <line x1={x(hoverX)} x2={x(hoverX)} y1={m.top} y2={height - m.bottom} stroke="var(--axis)" strokeWidth={1} />}
        {series.map((s) => (
          <g key={s.key}>
            <path d={path(s)} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
            {s.points.map((p) => p.y == null ? null : (
              <MarkerShape key={p.x} kind={s.marker} x={x(p.x)} y={y(p.y)} r={hoverX === p.x ? 5 : 3.5} color={s.color} />
            ))}
          </g>
        ))}
        {ends.map(({ s, x: ex, y: ey }) => (
          <text key={s.key} x={ex + 10} y={ey} dy="0.32em" fontSize={12} fill="var(--text-secondary)">{s.label}</text>
        ))}
      </svg>
      {tip.node}
    </div>
  );
}
