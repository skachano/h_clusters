// 3D structure (3Dmol.js), optionally animating one normal mode. Bonds are drawn either by
// distance (sticks) or, when bond orders are given, as one cylinder per bond whose thickness
// and opacity follow its order.
import { useEffect, useRef } from "react";
import { createViewer, type GLViewer, type Label } from "3dmol";
import type { BondOrder } from "../api/client";
import type { Halo } from "../lib/halos";
import { bondStyle, inFrame, parseXyz, principalFrame, setBonds } from "../lib/geometry";
import { useThemeVersion } from "../lib/theme";
import { useT } from "../i18n";

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

/** 3Dmol's zoomTo fits at least a 5 Å box; H clusters are often 1-3 Å across. */
export function smallZoom(xyz: string): number {
  const atoms = parseXyz(xyz);
  let extent = 0;
  for (let i = 0; i < atoms.length; i++)
    for (let j = i + 1; j < atoms.length; j++)
      extent = Math.max(extent, Math.hypot(atoms[i].x - atoms[j].x, atoms[i].y - atoms[j].y, atoms[i].z - atoms[j].z));
  return Math.min(4, Math.max(1, 5 / (extent + 0.6))); // 0.6 Å: room for the atom spheres
}

type Node3D = { material?: { depthWrite?: boolean }; children?: Node3D[] };

/**
 * Let transparent shapes (bonds, halos) show through each other, not only through the
 * opaque atoms.
 * 3Dmol first writes the depth of every transparent object, then draws only the frontmost
 * one at each pixel; a bond that writes no depth is blended back to front (3Dmol sorts
 * transparent objects by distance) instead. The material only exists once 3Dmol builds
 * the shape, so this wraps that step (GLShape.globj, 3Dmol 2.x).
 */
function seeThrough(shape: unknown) {
  const s = shape as { globj?: (group: unknown) => void; renderedShapeObj?: Node3D } | undefined;
  if (!s) return;
  const build = s.globj?.bind(s);
  if (!build) return;
  s.globj = (group) => {
    build(group);
    const visit = (o?: Node3D) => {
      if (!o) return;
      if (o.material) o.material.depthWrite = false;
      o.children?.forEach(visit);
    };
    visit(s.renderedShapeObj);
  };
}

/** Hover labels sit in the viewer's top-left corner: anchored at the atom they ran off the edge. */
function cornerLabel(text: string) {
  return {
    text,
    spec: {
      position: { x: 8, y: 8, z: 0 }, useScreen: true, alignment: "topLeft" as const,
      backgroundColor: cssVar("--surface-2", "#f3f3f0"), fontColor: cssVar("--text-primary", "#0b0b0b"),
      fontSize: 12, borderThickness: 0, inFront: true,
    },
  };
}

export function MoleculeViewer({ xyz, mode, bondOrders, atomLabels, halos, height = 340, label }: {
  xyz: string; mode?: number[][] | null; height?: number; label: string;
  /** Hover text per atom, in XYZ order. */
  atomLabels?: string[] | null;
  /** Charge or spin halos; null = no highlight. While highlighting, atoms turn neutral grey
   * so only the halos carry colour. Not drawn while a mode animates (shapes do not move). */
  halos?: Halo[] | null;
  /** Draw these instead of distance bonds (ignored while a mode animates: shapes do not move). */
  bondOrders?: BondOrder[] | null;
}) {
  const host = useRef<HTMLDivElement>(null);
  const viewer = useRef<GLViewer | null>(null);
  const themeVersion = useThemeVersion();
  const t = useT();

  useEffect(() => {
    // Rebuilt on a theme change: repainting a live WebGL canvas in the new colours left
    // light seams along its rounded corners.
    const el = host.current;
    if (!el) return;
    viewer.current = createViewer(el, {
      backgroundColor: cssVar("--surface-1", "#fcfcfb"),
      antialias: true,
    });
    const onResize = () => viewer.current?.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      viewer.current?.clear();
      viewer.current = null;
      el.replaceChildren(); // 3Dmol's canvases
    };
  }, [themeVersion]);

  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    v.stopAnimate();
    v.clear();
    const model = v.addModel(xyzWithMode(xyz, mode ?? null), "xyz", { assignBonds: false });
    const atoms = model.selectedAtoms({});
    const atom = halos ? cssVar("--text-muted", "#898781") : cssVar("--series-1", "#2a78d6");
    const byOrder = bondOrders && !mode;
    if (byOrder) {
      setBonds(atoms, "0\n\n"); // no sticks: every bond is a cylinder below
      v.setStyle({}, { sphere: { scale: 0.22, color: atom } });
      const ink = cssVar("--text-primary", "#0b0b0b"); // full contrast: opacity alone grades the bonds
      let hovered: Label | null = null;
      for (const b of bondOrders) {
        const style = bondStyle(b.order);
        const [p, q] = [atoms[b.i], atoms[b.j]];
        if (!style || !p || !q) continue;
        const start = { x: p.x ?? 0, y: p.y ?? 0, z: p.z ?? 0 };
        const end = { x: q.x ?? 0, y: q.y ?? 0, z: q.z ?? 0 };
        const d = Math.hypot(end.x - start.x, end.y - start.y, end.z - start.z);
        const cylinder = v.addCylinder({
          // 3Dmol applies a shape's opacity twice (it renders as opacity²): pass the square
          // root so the bond looks as opaque as bondStyle and the legend say.
          start, end, radius: style.radius, opacity: Math.sqrt(style.opacity), color: ink,
          hoverable: true,
          hover_callback: () => {
            const { text, spec } = cornerLabel(t("hover.bond", { pair: `H${b.i + 1}–H${b.j + 1}`, order: b.order.toFixed(2), d: d.toFixed(2) }));
            hovered = v.addLabel(text, spec);
          },
          unhover_callback: () => {
            if (hovered) v.removeLabel(hovered);
            hovered = null;
          },
        });
        seeThrough(cylinder);
      }
    } else {
      setBonds(atoms, xyz); // before vibrate(), which copies the atoms into frames
      const bond = cssVar("--axis", "#c3c2b7");
      v.setStyle({}, { sphere: { scale: 0.22, color: atom }, stick: { radius: 0.07, color: bond } });
    }
    if (halos && !mode) {
      for (const h of halos) {
        const a = atoms[h.i];
        if (!a) continue;
        seeThrough(v.addSphere({
          center: { x: a.x ?? 0, y: a.y ?? 0, z: a.z ?? 0 }, radius: h.radius,
          color: cssVar(h.color, "#898781"), opacity: Math.sqrt(h.opacity), // 3Dmol squares it
        }));
      }
    }
    if (atomLabels) {
      const labels = new Map<number, Label>();
      v.setHoverable({}, true, (a: { index?: number }) => {
        const i = a.index ?? -1;
        if (labels.has(i) || !atomLabels[i]) return;
        const { text, spec } = cornerLabel(atomLabels[i]);
        labels.set(i, v.addLabel(text, spec));
      }, (a: { index?: number }) => {
        const label = labels.get(a.index ?? -1);
        if (label) v.removeLabel(label);
        labels.delete(a.index ?? -1);
      });
    }
    v.setHoverDuration(150);
    if (mode) {
      model.vibrate(16, 0.6, true);
      v.animate({ loop: "backAndForth", interval: 45 });
    }
    v.zoomTo();
    v.zoom(0.85 * smallZoom(xyz));
    v.render();
  }, [xyz, mode, bondOrders, atomLabels, halos, themeVersion, t]);

  return (
    <div
      ref={host}
      role="img"
      aria-label={label}
      style={{ position: "relative", width: "100%", height, borderRadius: 8, overflow: "hidden" }}
    />
  );
}
