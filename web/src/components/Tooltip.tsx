// One fixed-position tooltip per chart. Content is React nodes (text is escaped by React).
import { useCallback, useState, type ReactNode } from "react";

interface TipState {
  x: number;
  y: number;
  content: ReactNode;
}

export function useTooltip() {
  const [tip, setTip] = useState<TipState | null>(null);
  const show = useCallback((x: number, y: number, content: ReactNode) => setTip({ x, y, content }), []);
  const hide = useCallback(() => setTip(null), []);
  const node = tip ? (
    <div
      className="tooltip"
      role="status"
      style={{
        left: Math.min(tip.x + 14, window.innerWidth - 290),
        top: Math.max(8, tip.y + 14),
      }}
    >
      {tip.content}
    </div>
  ) : null;
  return { show, hide, node };
}

/** Show at a focused element's position (keyboard users get the same details as hover). */
export function focusPoint(e: React.FocusEvent<Element>): [number, number] {
  const r = e.currentTarget.getBoundingClientRect();
  return [r.left + r.width / 2, r.top + r.height / 2];
}
