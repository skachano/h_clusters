// 3D structure (3Dmol.js), optionally animating one normal mode.
import { useEffect, useRef } from "react";
import { createViewer, type GLViewer } from "3dmol";
import { inFrame, parseXyz, principalFrame } from "../lib/geometry";

function cssVar(name: string, fallback: string) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

/**
 * XYZ rotated onto the principal axes (the viewer looks down the smallest one, so it shows the
 * most of the shape), with per-atom displacement columns that 3Dmol reads as vibrations.
 */
export function xyzWithMode(xyz: string, mode: number[][] | null): string {
  const atoms = parseXyz(xyz);
  const { center, axes } = principalFrame(atoms);
  const lines = atoms.map((a, i) => {
    const [x, y, z] = inFrame([a.x - center[0], a.y - center[1], a.z - center[2]], axes);
    const d = mode ? inFrame(mode[i], axes) : null;
    return `${a.symbol} ${x} ${y} ${z}${d ? ` ${d[0]} ${d[1]} ${d[2]}` : ""}`;
  });
  return `${atoms.length}\n\n${lines.join("\n")}\n`;
}

export function MoleculeViewer({ xyz, mode, height = 340, label }: {
  xyz: string; mode?: number[][] | null; height?: number; label: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const viewer = useRef<GLViewer | null>(null);

  useEffect(() => {
    if (!host.current) return;
    viewer.current = createViewer(host.current, {
      backgroundColor: cssVar("--surface-1", "#fcfcfb"),
      antialias: true,
    });
    const onResize = () => viewer.current?.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      viewer.current?.clear();
      viewer.current = null;
    };
  }, []);

  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    v.stopAnimate();
    v.clear();
    const model = v.addModel(xyzWithMode(xyz, mode ?? null), "xyz");
    const atom = cssVar("--series-1", "#2a78d6");
    const bond = cssVar("--axis", "#c3c2b7");
    v.setStyle({}, { sphere: { scale: 0.22, color: atom }, stick: { radius: 0.07, color: bond } });
    if (mode) {
      model.vibrate(16, 0.6, true);
      v.animate({ loop: "backAndForth", interval: 45 });
    }
    v.zoomTo();
    v.zoom(0.85);
    v.render();
  }, [xyz, mode]);

  return (
    <div
      ref={host}
      role="img"
      aria-label={label}
      style={{ position: "relative", width: "100%", height, borderRadius: 8, overflow: "hidden" }}
    />
  );
}
