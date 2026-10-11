// Horizontal bars from a zero baseline: positive (bound) in blue, negative in red, values at
// the bar ends. Used for the fragmentation channels of one state; the weakest is marked.
import { linear, niceExtent, tickLabel, ticks } from "./frame";
import { pretty, signed } from "../../lib/format";
import { useT } from "../../i18n";

export interface Bar {
  key: string;
  label: string;
  sublabel?: string;
  value: number | null;
}

export function DivergingBars({ bars, unit, highlight }: { bars: Bar[]; unit: string; highlight?: string }) {
  const t = useT();
  const rowH = 30;
  const labelW = 170;
  const width = 640;
  const m = { top: 6, right: 64, bottom: 26, left: labelW + 8 };
  const values = bars.flatMap((b) => (b.value == null ? [] : [b.value]));
  const domain = niceExtent(values, 0, 4);
  const x = linear(domain, [m.left, width - m.right]);
  const height = m.top + bars.length * rowH + m.bottom;
  const barH = 14;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" role="img" aria-label={t("chart.channels")} style={{ display: "block" }}>
      {ticks(domain[0], domain[1], 4).map((t) => (
        <g key={t}>
          <line x1={x(t)} x2={x(t)} y1={m.top} y2={height - m.bottom} stroke={t === 0 ? "var(--axis)" : "var(--grid)"} />
          <text x={x(t)} y={height - 8} textAnchor="middle" fontSize={11} fill="var(--text-muted)" className="num">{tickLabel(t)}</text>
        </g>
      ))}
      {bars.map((b, i) => {
        const cy = m.top + i * rowH + rowH / 2;
        const v = b.value;
        const strong = b.key === highlight;
        return (
          <g key={b.key}>
            <text x={0} y={cy - (b.sublabel ? 5 : 0)} dy="0.32em" fontSize={12} fill="var(--text-primary)" fontWeight={strong ? 600 : 400}>
              {pretty(b.label)}
            </text>
            {b.sublabel && (
              <text x={0} y={cy + 9} dy="0.32em" fontSize={10.5} fill="var(--text-muted)">→ {pretty(b.sublabel)}</text>
            )}
            {v != null && (() => {
              const x0 = x(0);
              const x1 = x(v);
              const left = Math.min(x0, x1);
              const w = Math.max(1, Math.abs(x1 - x0));
              const r = Math.min(4, w / 2);
              const fill = v >= 0 ? "var(--div-pos-2)" : "var(--div-neg-2)";
              // rounded at the data end, square at the baseline
              const d = v >= 0
                ? `M${left},${cy - barH / 2} H${left + w - r} Q${left + w},${cy - barH / 2} ${left + w},${cy - barH / 2 + r} V${cy + barH / 2 - r} Q${left + w},${cy + barH / 2} ${left + w - r},${cy + barH / 2} H${left} Z`
                : `M${left + w},${cy - barH / 2} H${left + r} Q${left},${cy - barH / 2} ${left},${cy - barH / 2 + r} V${cy + barH / 2 - r} Q${left},${cy + barH / 2} ${left + r},${cy + barH / 2} H${left + w} Z`;
              return (
                <>
                  <path d={d} fill={fill} />
                  <text x={v >= 0 ? left + w + 6 : left - 6} y={cy} dy="0.32em" textAnchor={v >= 0 ? "start" : "end"}
                    fontSize={11.5} fill="var(--text-secondary)" className="num" fontWeight={strong ? 600 : 400}>
                    {signed(v, 3)}
                  </text>
                </>
              );
            })()}
          </g>
        );
      })}
      <text x={width - m.right} y={height - 8} textAnchor="end" dx={56} fontSize={11} fill="var(--text-muted)">{unit}</text>
    </svg>
  );
}
