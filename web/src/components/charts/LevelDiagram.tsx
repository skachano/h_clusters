// An energy-level diagram: one short horizontal line per isomer or spin state at its relative
// energy (eV), labelled beside it. Clicking a level selects it.
import { linear, niceExtent, tickLabel, ticks } from "./frame";

export interface Level {
  key: string;
  label: string;
  value: number;
  selected?: boolean;
}

export function LevelDiagram({ levels, unit, onSelect, height = 220, ariaLabel }: {
  levels: Level[]; unit: string; onSelect?: (key: string) => void; height?: number; ariaLabel: string;
}) {
  const width = 300;
  const m = { top: 12, right: 8, bottom: 12, left: 48 };
  const domain = niceExtent(levels.map((l) => l.value), 0, 4);
  const y = linear(domain, [height - m.bottom, m.top]);
  // lay levels out in columns so close energies do not overlap
  const placed: { level: Level; col: number }[] = [];
  for (const level of [...levels].sort((a, b) => a.value - b.value)) {
    let col = 0;
    while (placed.some((p) => p.col === col && Math.abs(y(p.level.value) - y(level.value)) < 14)) col++;
    placed.push({ level, col });
  }
  const colW = 110;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" role="group" aria-label={ariaLabel} style={{ display: "block", maxWidth: width }}>
      {ticks(domain[0], domain[1], 4).map((t) => (
        <g key={t}>
          <line x1={m.left} x2={width - m.right} y1={y(t)} y2={y(t)} stroke="var(--grid)" />
          <text x={m.left - 6} y={y(t)} dy="0.32em" textAnchor="end" fontSize={10.5} fill="var(--text-muted)" className="num">{tickLabel(t)}</text>
        </g>
      ))}
      {placed.map(({ level, col }) => {
        const x0 = m.left + 8 + col * colW;
        const yy = y(level.value);
        return (
          <g key={level.key} role={onSelect ? "button" : undefined} tabIndex={onSelect ? 0 : undefined}
            aria-pressed={onSelect ? !!level.selected : undefined}
            aria-label={`${level.label}: ${level.value.toFixed(3)} ${unit}`}
            onClick={() => onSelect?.(level.key)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect?.(level.key); } }}
            style={{ cursor: onSelect ? "pointer" : "default", outline: "none" }}>
            <rect x={x0 - 4} y={yy - 9} width={colW - 6} height={18} fill="transparent" />
            <line x1={x0} x2={x0 + 28} y1={yy} y2={yy} stroke={level.selected ? "var(--series-1)" : "var(--text-secondary)"} strokeWidth={level.selected ? 3 : 2} strokeLinecap="round" />
            <text x={x0 + 34} y={yy} dy="0.32em" fontSize={11} fill={level.selected ? "var(--text-primary)" : "var(--text-secondary)"} fontWeight={level.selected ? 600 : 400}>
              {level.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
