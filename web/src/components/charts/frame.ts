import { useEffect, useRef, useState } from "react";

// Small helpers shared by the SVG charts: linear scales and clean ticks.

export interface Scale {
  (v: number): number;
  domain: [number, number];
  range: [number, number];
}

export function linear(domain: [number, number], range: [number, number]): Scale {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const k = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
  const s = ((v: number) => r0 + (v - d0) * k) as Scale;
  s.domain = domain;
  s.range = range;
  return s;
}

/** Round tick values covering [lo, hi], about `count` of them. */
export function ticks(lo: number, hi: number, count = 5): number[] {
  if (!(hi > lo)) return [lo];
  const raw = (hi - lo) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((f) => f * mag).find((s) => s >= raw) ?? 10 * mag;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(Number(v.toPrecision(12)));
  return out;
}

/** Pad a [min, max] extent and snap it to ticks; always include `include` (e.g. 0). */
export function niceExtent(values: number[], include?: number, count = 5): [number, number] {
  const finite = values.filter(Number.isFinite);
  let lo = Math.min(...finite, include ?? Infinity);
  let hi = Math.max(...finite, include ?? -Infinity);
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return [0, 1];
  if (lo === hi) {
    lo -= 1;
    hi += 1;
  }
  const t = ticks(lo, hi, count);
  const step = t.length > 1 ? t[1] - t[0] : 1;
  return [Math.floor(lo / step) * step, Math.ceil(hi / step) * step];
}

export const tickLabel = (v: number) => (Math.abs(v) >= 1000 ? v.toLocaleString() : String(Number(v.toPrecision(6))));


/** The rendered width of an element, so SVG text stays at its native size at any width. */
export function useWidth<T extends HTMLElement>(fallback = 720) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setWidth(Math.max(280, Math.round(el.getBoundingClientRect().width)));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}
