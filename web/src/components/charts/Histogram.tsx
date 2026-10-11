// Counts per bin over log-spaced edges (wall times). One series: no legend, the title names it.
import { focusPoint, useTooltip } from "../Tooltip";
import { duration } from "../../lib/format";
import { linear, ticks } from "./frame";
import { useT } from "../../i18n";

export function Histogram({ edges, counts, height = 120, label }: {
  edges: number[]; counts: number[]; height?: number; label: string;
}) {
  const t = useT();
  const tip = useTooltip();
  const width = 300;
  const m = { top: 8, right: 8, bottom: 28, left: 34 };
  const first = counts.findIndex((c) => c > 0);
  const last = counts.length - 1 - [...counts].reverse().findIndex((c) => c > 0);
  if (first < 0) return <p className="muted">{t("chart.noRuns")}</p>;
  const lo = Math.max(0, first - 1);
  const hi = Math.min(counts.length - 1, last + 1);
  const shown = counts.slice(lo, hi + 1);
  const max = Math.max(...shown);
  const yTicks = ticks(0, max, 3).filter((t) => Number.isInteger(t));
  const y = linear([0, Math.max(...yTicks, max)], [height - m.bottom, m.top]);
  const band = (width - m.left - m.right) / shown.length;
  const barW = Math.min(24, band - 2);

  const describe = (i: number) => (
    <div>
      <div className="tt-value">{t("chart.runs", { n: shown[i] })}</div>
      <div className="tt-label">{duration(edges[lo + i])} – {duration(edges[lo + i + 1])}</div>
    </div>
  );

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" role="img" aria-label={label} style={{ display: "block" }}>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={m.left} x2={width - m.right} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--axis)" : "var(--grid)"} />
            <text x={m.left - 6} y={y(t)} dy="0.32em" textAnchor="end" fontSize={10} fill="var(--text-muted)" className="num">{t}</text>
          </g>
        ))}
        {shown.map((c, i) => {
          const x0 = m.left + i * band + (band - barW) / 2;
          const top = y(c);
          const h = y(0) - top;
          const r = Math.min(4, h / 2, barW / 2);
          return (
            <g key={i} tabIndex={c ? 0 : -1}
              onPointerMove={(e) => tip.show(e.clientX, e.clientY, describe(i))} onPointerLeave={tip.hide}
              onFocus={(e) => tip.show(...focusPoint(e), describe(i))} onBlur={tip.hide}
              style={{ outline: "none" }}>
              <rect x={m.left + i * band} y={m.top} width={band} height={height - m.top - m.bottom} fill="transparent" />
              {c > 0 && (
                <path
                  d={`M${x0},${y(0)} V${top + r} Q${x0},${top} ${x0 + r},${top} H${x0 + barW - r} Q${x0 + barW},${top} ${x0 + barW},${top + r} V${y(0)} Z`}
                  fill="var(--series-1)"
                />
              )}
            </g>
          );
        })}
        {[0, Math.floor(shown.length / 2), shown.length].map((i, k) => (
          <text key={i} x={m.left + i * band} y={height - 10} textAnchor={(["start", "middle", "end"] as const)[k]} fontSize={10} fill="var(--text-muted)">
            {duration(edges[lo + i])}
          </text>
        ))}
      </svg>
      {tip.node}
    </div>
  );
}
