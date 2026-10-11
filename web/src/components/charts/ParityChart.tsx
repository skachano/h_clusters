// Test level against reference, one dot per state, coloured by charge (≤ 3 categorical slots,
// valid for all-pairs forms). The diagonal is perfect agreement. 24px hit areas per dot.
import { useMemo } from "react";
import { focusPoint, useTooltip } from "../Tooltip";
import { linear, niceExtent, tickLabel, ticks } from "./frame";

export interface ParityPoint {
  key: string;
  label: string;
  x: number;
  y: number;
  group: number;
}

export function ParityChart({ points, groups, xLabel, yLabel, unit, size = 380 }: {
  points: ParityPoint[]; groups: { key: number; label: string; color: string }[];
  xLabel: string; yLabel: string; unit: string; size?: number;
}) {
  const tip = useTooltip();
  const m = { top: 12, right: 12, bottom: 44, left: 52 };
  const { s, t } = useMemo(() => {
    const extent = niceExtent(points.flatMap((p) => [p.x, p.y]), 0);
    return { s: extent, t: ticks(extent[0], extent[1], 5) };
  }, [points]);
  const x = linear(s, [m.left, size - m.right]);
  const y = linear(s, [size - m.bottom, m.top]);
  const color = Object.fromEntries(groups.map((g) => [g.key, g.color]));

  const describe = (p: ParityPoint) => (
    <div>
      <div className="tt-value">{p.label}</div>
      <div className="tt-label">{xLabel}: {p.x.toFixed(3)} {unit}</div>
      <div className="tt-label">{yLabel}: {p.y.toFixed(3)} {unit}</div>
      <div className="tt-label">error: {(p.y - p.x >= 0 ? "+" : "−") + Math.abs(p.y - p.x).toFixed(3)} {unit}</div>
    </div>
  );

  return (
    <div>
      <div className="legend" style={{ marginBottom: 8 }}>
        {groups.map((g) => (
          <span className="legend-item" key={g.key}>
            <span className="swatch" style={{ background: g.color, borderRadius: "50%" }} />
            {g.label}
          </span>
        ))}
        <span className="legend-item"><span className="line-key" style={{ background: "var(--axis)" }} />perfect agreement</span>
      </div>
      <svg viewBox={`0 0 ${size} ${size}`} width="100%" style={{ maxWidth: size, display: "block" }} role="img"
        aria-label={`${yLabel} against ${xLabel}`}>
        {t.map((v) => (
          <g key={v}>
            <line x1={m.left} x2={size - m.right} y1={y(v)} y2={y(v)} stroke="var(--grid)" />
            <line y1={m.top} y2={size - m.bottom} x1={x(v)} x2={x(v)} stroke="var(--grid)" />
            <text x={m.left - 6} y={y(v)} dy="0.32em" textAnchor="end" fontSize={11} fill="var(--text-muted)" className="num">{tickLabel(v)}</text>
            <text x={x(v)} y={size - m.bottom + 16} textAnchor="middle" fontSize={11} fill="var(--text-muted)" className="num">{tickLabel(v)}</text>
          </g>
        ))}
        <line x1={x(s[0])} y1={y(s[0])} x2={x(s[1])} y2={y(s[1])} stroke="var(--axis)" strokeWidth={1.5} />
        <text x={(m.left + size - m.right) / 2} y={size - 6} textAnchor="middle" fontSize={12} fill="var(--text-secondary)">{xLabel} ({unit})</text>
        <text transform={`translate(12 ${(m.top + size - m.bottom) / 2}) rotate(-90)`} textAnchor="middle" fontSize={12} fill="var(--text-secondary)">{yLabel} ({unit})</text>
        {points.map((p) => (
          <g
            key={p.key} tabIndex={0} role="img" aria-label={`${p.label}: ${p.x.toFixed(3)} vs ${p.y.toFixed(3)} ${unit}`}
            onPointerMove={(e) => tip.show(e.clientX, e.clientY, describe(p))}
            onPointerLeave={tip.hide}
            onFocus={(e) => tip.show(...focusPoint(e), describe(p))}
            onBlur={tip.hide}
            style={{ cursor: "default", outline: "none" }}
          >
            <circle cx={x(p.x)} cy={y(p.y)} r={12} fill="transparent" />
            <circle cx={x(p.x)} cy={y(p.y)} r={4.5} fill={color[p.group]} stroke="var(--surface-1)" strokeWidth={2} />
          </g>
        ))}
      </svg>
      {tip.node}
    </div>
  );
}
