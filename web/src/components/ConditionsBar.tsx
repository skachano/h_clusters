// Temperature and pressure (log sliders), and the plotted quantity: one row above the content.
import { useEffect, useState } from "react";
import { P_RANGE, QUANTITIES, T_RANGE, type ColorBy } from "../lib/conditions";
import { useManifest, type Conditions, type Quantity } from "../api/client";
import { nearestIndex } from "../api/static";
import { useT, type Key } from "../i18n";

const log = Math.log10;

function LogSlider({ id, label, value, range, unit, format, onChange, grid }: {
  id: string; label: string; value: number; range: readonly [number, number]; unit: string;
  format: (v: number) => string; onChange: (v: number) => void;
  /** Static site: the slider steps through these exported values only. */
  grid?: number[];
}) {
  // Local state while dragging; the URL (and the request) follows after a short pause.
  const [local, setLocal] = useState(value);
  useEffect(() => setLocal(value), [value]);
  useEffect(() => {
    if (local === value) return;
    const t = setTimeout(() => onChange(local), 120);
    return () => clearTimeout(t);
  }, [local, value, onChange]);
  return (
    <div className="control">
      <label htmlFor={id}>
        {label} <output htmlFor={id}>{format(local)} {unit}</output>
      </label>
      <input
        id={id} type="range" min={log(range[0])} max={log(range[1])} step={0.01}
        value={log(local)}
        onChange={(e) => {
          const v = 10 ** Number(e.target.value);
          setLocal(grid ? grid[nearestIndex(grid, v)] : Number(v.toPrecision(4)));
        }}
      />
    </div>
  );
}

export function Segmented<T extends string>({ label, value, options, onChange }: {
  label: string; value: T; options: { value: T; label: string; title?: string }[]; onChange: (v: T) => void;
}) {
  return (
    <div className="control">
      <span className="label">{label}</span>
      <div className="segmented" role="group" aria-label={label}>
        {options.map((o) => (
          <button key={o.value} type="button" title={o.title} aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ConditionsBar({ conditions, quantity, colorBy, update, children }: {
  conditions: Conditions; quantity?: Quantity; colorBy?: ColorBy;
  update: (changes: Record<string, string | number | null>) => void; children?: React.ReactNode;
}) {
  const thermal = quantity === "d_h" || quantity === "d_g";
  const grid = useManifest().data?.conditions;
  const t = useT();
  return (
    <div className="controls">
      {children}
      {colorBy && (
        <Segmented<ColorBy>
          label={t("cond.colourBy")} value={colorBy} onChange={(v) => update({ color: v })}
          options={[{ value: "verdict", label: t("cond.byVerdict") }, { value: "value", label: t("cond.byEnergy") }]}
        />
      )}
      {quantity && (
        <Segmented<Quantity>
          label={t("cond.dissociation")} value={quantity} onChange={(v) => update({ q: v })}
          options={QUANTITIES.map((q) => ({ value: q.value, label: q.label, title: t(`q.${q.value}` as Key) }))}
        />
      )}
      <LogSlider
        id="temperature" label={t("cond.temperature")} value={conditions.temperature} range={T_RANGE} unit="K"
        format={(v) => (v >= 100 ? v.toFixed(0) : v.toFixed(1))} onChange={(v) => update({ T: v })}
        grid={grid?.temperatures}
      />
      <LogSlider
        id="pressure" label={t("cond.pressure")} value={conditions.pressure} range={P_RANGE} unit="atm"
        format={(v) => (v >= 0.01 && v < 1000 ? v.toPrecision(3) : v.toExponential(1))}
        onChange={(v) => update({ p: v })} grid={grid?.pressures}
      />
      {quantity && !thermal && (
        <span className="hint">{t("cond.thermalOnly")}</span>
      )}
      {grid && (
        <span className="hint">{t("cond.static", { nt: grid.temperatures.length, np: grid.pressures.length })}</span>
      )}
    </div>
  );
}
