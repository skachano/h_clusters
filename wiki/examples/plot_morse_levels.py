"""Write morse_levels.svg.html: H2's well with its vibrational levels, D_e and D_0.

Uses a Morse potential, V(R) = D_e (1 - exp(-a (R - R_e)))^2, fitted to H2's
well depth and harmonic frequency. A Morse oscillator has exact levels

    E_v = w (v + 1/2) - w x (v + 1/2)^2,   w x = w^2 / (4 D_e)

so the zero-point energy and D_0 follow from two measured numbers. Rerun:

    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/plot_morse_levels.py
"""

import math
from pathlib import Path

import numpy as np

EV_PER_CM = 1 / 8065.544  # 1 cm^-1 in eV
AMU, C_CM, EV = 1.66053907e-27, 2.99792458e10, 1.602176634e-19

D_E = 4.75  # eV, H2 well depth
R_E = 0.741  # Å
OMEGA = 4401.2  # cm^-1, H2 harmonic frequency
MU = 1.00782503 / 2  # amu, reduced mass of two H atoms

W, H = 680, 400
LEFT, RIGHT, TOP, BOTTOM = 64, 150, 24, 52
X_RANGE = (0.3, 3.2)  # Å
Y_RANGE = (-0.7, 5.4)  # eV above the bottom of the well


def morse_a():
    """Morse range parameter (1/Å) from the force constant k = mu w^2 = 2 a^2 D_e."""
    omega = 2 * math.pi * C_CM * OMEGA
    k = MU * AMU * omega**2
    return math.sqrt(k / (2 * D_E * EV)) * 1e-10


def levels():
    """Energies (eV, from the well bottom) of the bound Morse levels."""
    wx = OMEGA**2 / (4 * D_E / EV_PER_CM)
    v_max = math.ceil(OMEGA / (2 * wx) - 0.5) - 1  # bound states need v + 1/2 < w / (2 w x)
    return [(OMEGA * (v + 0.5) - wx * (v + 0.5) ** 2) * EV_PER_CM for v in range(v_max + 1)]


def x_px(r):
    return LEFT + (r - X_RANGE[0]) / (X_RANGE[1] - X_RANGE[0]) * (W - LEFT - RIGHT)


def y_px(e):
    return TOP + (Y_RANGE[1] - e) / (Y_RANGE[1] - Y_RANGE[0]) * (H - TOP - BOTTOM)


def arrow(x, y_from, y_to, cls):
    """Vertical double-headed arrow."""
    return (
        f'<line class="{cls}" x1="{x:.1f}" x2="{x:.1f}" y1="{y_from:.1f}" y2="{y_to:.1f}" '
        'marker-start="url(#viz-arrow)" marker-end="url(#viz-arrow)"/>'
    )


def main():
    a = morse_a()
    lv = levels()
    zpe = lv[0]

    def V(r):
        return D_E * (1 - np.exp(-a * (r - R_E))) ** 2

    def turning_points(e):
        s = math.sqrt(e / D_E)
        return R_E - math.log(1 + s) / a, R_E - math.log(1 - s) / a

    r = np.linspace(R_E - math.log(1 + math.sqrt(Y_RANGE[1] / D_E)) / a, X_RANGE[1], 200)
    out = ['<div class="viz" markdown="0">']
    out.append(
        f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="H2 potential well with its '
        f'vibrational levels; D_e = {D_E:.2f} eV, zero-point energy {zpe:.2f} eV, '
        f'D_0 = {D_E - zpe:.2f} eV">'
    )
    out.append(
        # refX at the arrow tip, so the tip lands exactly on the line's end point.
        '<defs><marker id="viz-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse"><path d="M0 1 L9 5 L0 9 z" class="viz-arrowhead"/>'
        "</marker></defs>"
    )
    # Axes.
    out.append(f'<line class="viz-axis" x1="{LEFT}" x2="{W - RIGHT}" y1="{H - BOTTOM}" y2="{H - BOTTOM}"/>')
    for t in np.arange(0.5, 3.01, 0.5):
        out.append(f'<text class="viz-tick" x="{x_px(t):.1f}" y="{H - BOTTOM + 18}" text-anchor="middle">{t:.1f}</text>')
    for e in range(0, 6):
        y = y_px(e)
        out.append(f'<line class="viz-grid" x1="{LEFT}" x2="{W - RIGHT}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="viz-tick" x="{LEFT - 8}" y="{y + 4:.1f}" text-anchor="end">{e}</text>')
    out.append(
        f'<text class="viz-title" x="{(LEFT + W - RIGHT) / 2}" y="{H - 10}" text-anchor="middle">'
        "Bond length R (Å)</text>"
    )
    out.append(
        f'<text class="viz-title" transform="translate(16 {(TOP + H - BOTTOM) / 2}) rotate(-90)" '
        'text-anchor="middle">Energy above the minimum (eV)</text>'
    )
    # Dissociation limit.
    y_lim = y_px(D_E)
    out.append(f'<line class="viz-ref" x1="{LEFT}" x2="{W - RIGHT}" y1="{y_lim:.1f}" y2="{y_lim:.1f}"/>')
    out.append(f'<text class="viz-label" x="{W - RIGHT + 8}" y="{y_lim + 4:.1f}">H + H, far apart</text>')
    # Vibrational levels, each drawn between its classical turning points.
    for v, e in enumerate(lv):
        r1, r2 = turning_points(e)
        r2 = min(r2, X_RANGE[1])  # levels near the top extend past the plot
        y = y_px(e)
        cls = "viz-level s1" if v == 0 else "viz-level"
        out.append(
            f'<g class="viz-pt"><title>v = {v}: {e:.3f} eV above the minimum</title>'
            f'<line class="viz-hit-line" x1="{x_px(r1):.1f}" x2="{x_px(r2):.1f}" y1="{y:.1f}" y2="{y:.1f}"/>'
            f'<line class="{cls}" x1="{x_px(r1):.1f}" x2="{x_px(r2):.1f}" y1="{y:.1f}" y2="{y:.1f}"/></g>'
        )
    for v in (0, 1, 2):
        _, r2 = turning_points(lv[v])
        out.append(f'<text class="viz-note" x="{x_px(r2) + 6:.1f}" y="{y_px(lv[v]) + 4:.1f}">v = {v}</text>')
    out.append(
        f'<text class="viz-note" x="{x_px(2.05):.1f}" y="{y_px(lv[-1]) - 14:.1f}">'
        f"v = {len(lv) - 1} (last bound level)</text>"
    )
    # Potential curve on top of the levels.
    pts = " ".join(f"{x_px(ri):.1f},{y_px(V(ri)):.1f}" for ri in r)
    out.append(f'<polyline class="viz-line s2" points="{pts}"/>')
    # Minimum.
    out.append(f'<circle class="viz-dot s2" cx="{x_px(R_E):.1f}" cy="{y_px(0):.1f}" r="4"/>')
    out.append(
        f'<text class="viz-note" x="{x_px(R_E):.1f}" y="{y_px(0) + 20:.1f}" text-anchor="middle">'
        f'minimum, R<tspan baseline-shift="sub" font-size="9">e</tspan> = {R_E} Å</text>'
    )
    # D_e, D_0 and ZPE arrows, right of the well.
    x_de, x_d0 = x_px(2.55), x_px(2.9)
    out.append(arrow(x_de, y_px(0), y_lim, "viz-arrow-line"))
    out.append(arrow(x_d0, y_px(zpe), y_lim, "viz-arrow-line"))
    out.append(f'<line class="viz-ref" x1="{x_px(1.0):.1f}" x2="{x_d0 + 10:.1f}" y1="{y_px(0):.1f}" y2="{y_px(0):.1f}"/>')
    out.append(
        f'<line class="viz-ref" x1="{x_px(1.15):.1f}" x2="{x_d0 + 10:.1f}" y1="{y_px(zpe):.1f}" y2="{y_px(zpe):.1f}"/>'
    )
    y_mid = y_px(D_E / 2)
    out.append(f'<text class="viz-label" x="{x_de - 10:.1f}" y="{y_mid:.1f}" text-anchor="end">D<tspan baseline-shift="sub" font-size="9">e</tspan></text>')
    out.append(f'<text class="viz-note" x="{x_de - 10:.1f}" y="{y_mid + 15:.1f}" text-anchor="end">{D_E:.2f} eV</text>')
    out.append(f'<text class="viz-label" x="{x_d0 + 10:.1f}" y="{y_mid:.1f}">D<tspan baseline-shift="sub" font-size="9">0</tspan></text>')
    out.append(f'<text class="viz-note" x="{x_d0 + 10:.1f}" y="{y_mid + 15:.1f}">{D_E - zpe:.2f} eV</text>')
    out.append(
        f'<text class="viz-note" x="{x_d0 + 16:.1f}" y="{(y_px(0) + y_px(zpe)) / 2 + 4:.1f}">'
        f"ZPE {zpe:.2f} eV</text>"
    )
    out.append("</svg></div>")

    path = Path(__file__).with_name("morse_levels.svg.html")
    path.write_text("\n".join(out) + "\n")
    print(f"a = {a:.3f} 1/Å, {len(lv)} bound levels, ZPE = {zpe:.4f} eV, D_0 = {D_E - zpe:.3f} eV")
    print(f"v=0 -> v=1 gap: {(lv[1] - lv[0]) / EV_PER_CM:.0f} cm^-1")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
