"""Write h2_pes.svg.html: the H2/STO-3G energy curve as an inline SVG for the wiki.

The pages include the output with pymdownx.snippets, so it follows the
wiki's light/dark theme (colors come from wiki/pages/stylesheets/extra.css).
Rerun after changing h2_minimal_basis.py:

    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/plot_h2_pes.py
"""

from pathlib import Path

import numpy as np

from h2_minimal_basis import BOHR_TO_ANGSTROM, hydrogen_atom_energy, scan

W, H = 680, 380
LEFT, RIGHT, TOP, BOTTOM = 64, 80, 16, 52
X_RANGE = (0.3, 3.2)  # Å
Y_RANGE = (-1.2, -0.4)  # hartree
MARKER_R = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0]  # bohr, as in the page table


def minus(v, digits):
    """Format with a typographic minus sign."""
    return f"{v:.{digits}f}".replace("-", "\u2212")


def x_px(r):
    return LEFT + (r - X_RANGE[0]) / (X_RANGE[1] - X_RANGE[0]) * (W - LEFT - RIGHT)


def y_px(e):
    return TOP + (Y_RANGE[1] - e) / (Y_RANGE[1] - Y_RANGE[0]) * (H - TOP - BOTTOM)


def main():
    curve = scan(np.arange(0.6, 6.001, 0.05))
    markers = scan(MARKER_R)
    fine = scan(np.arange(1.30, 1.50, 0.005))
    R_min, _, E_min = min(fine, key=lambda row: row[2])
    two_E_H = 2 * hydrogen_atom_energy()

    out = ['<div class="viz" markdown="0">']
    out.append(
        '<div class="viz-legend">'
        '<span><i class="viz-key s1"></i>Hartree–Fock (RHF)</span>'
        '<span><i class="viz-key s2"></i>Full CI (exact in this basis)</span></div>'
    )
    out.append(
        f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Energy of H2 versus bond length, '
        'STO-3G basis, Hartree-Fock and full CI">'
    )
    # Grid and axes.
    for e in np.arange(Y_RANGE[0], Y_RANGE[1] + 1e-9, 0.2):
        y = y_px(e)
        out.append(f'<line class="viz-grid" x1="{LEFT}" x2="{W - RIGHT}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="viz-tick" x="{LEFT - 8}" y="{y + 4:.1f}" text-anchor="end">{minus(e, 1)}</text>')
    for r in np.arange(0.5, 3.01, 0.5):
        x = x_px(r)
        out.append(f'<text class="viz-tick" x="{x:.1f}" y="{H - BOTTOM + 18}" text-anchor="middle">{r:.1f}</text>')
    out.append(f'<line class="viz-axis" x1="{LEFT}" x2="{W - RIGHT}" y1="{H - BOTTOM}" y2="{H - BOTTOM}"/>')
    out.append(
        f'<text class="viz-title" x="{(LEFT + W - RIGHT) / 2}" y="{H - 10}" text-anchor="middle">'
        "Bond length R (Å)</text>"
    )
    out.append(
        f'<text class="viz-title" transform="translate(16 {(TOP + H - BOTTOM) / 2}) rotate(-90)" '
        'text-anchor="middle">Energy (hartree)</text>'
    )
    # Reference: two separated H atoms.
    y_ref = y_px(two_E_H)
    out.append(f'<line class="viz-ref" x1="{LEFT}" x2="{W - RIGHT}" y1="{y_ref:.1f}" y2="{y_ref:.1f}"/>')
    out.append(
        f'<text class="viz-note" x="{x_px(1.9):.1f}" y="{y_ref - 12:.1f}">'
        f"2 E(H) = {minus(two_E_H, 3)}: two separate atoms</text>"
    )
    # Curves, then markers with tooltips on top.
    for cls, col in [("s1", 1), ("s2", 2)]:
        pts = " ".join(f"{x_px(row[0] * BOHR_TO_ANGSTROM):.1f},{y_px(row[col]):.1f}" for row in curve)
        out.append(f'<polyline class="viz-line {cls}" points="{pts}"/>')
    for cls, col, name in [("s1", 1, "RHF"), ("s2", 2, "FCI")]:
        for row in markers:
            r = row[0] * BOHR_TO_ANGSTROM
            x, y = x_px(r), y_px(row[col])
            out.append(
                f'<g class="viz-pt {cls}"><title>{name}: R = {r:.3f} Å, E = {row[col]:.4f} hartree</title>'
                f'<circle class="viz-hit" cx="{x:.1f}" cy="{y:.1f}" r="10"/>'
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4"/></g>'
            )
    # Direct labels at the curve ends and at the minimum.
    for name, col in [("RHF", 1), ("FCI", 2)]:
        out.append(
            f'<text class="viz-label" x="{W - RIGHT + 8}" y="{y_px(curve[-1][col]) + 4:.1f}">{name}</text>'
        )
    x_min, y_min = x_px(R_min * BOHR_TO_ANGSTROM), y_px(E_min)
    out.append(
        f'<text class="viz-note" x="{x_min:.1f}" y="{y_min + 22:.1f}" text-anchor="middle">'
        f"minimum: R = {R_min * BOHR_TO_ANGSTROM:.2f} Å</text>"
    )
    out.append("</svg></div>")

    path = Path(__file__).with_name("h2_pes.svg.html")
    path.write_text("\n".join(out) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
