"""Static electric field: polarization of H2 and field-induced (de)stabilization of the
neutral van der Waals clusters.

Only neutral species: in a uniform field the energy of an ion depends on where it sits
(E = q F·r), so a relaxed ion would just drift. The field points along z; each structure
starts with its longest axis along z and relaxes (ORCA optimizes in Cartesians with a field),
so molecules can turn to align. 0.01 a.u. = 0.514 V/Å.

The torque is tiny (alpha anisotropy x F^2 ~ 1e-5 Eh/rad^2), about the size of the DFT
integration-grid noise under rotation, so with the default grid the optimizer wanders in
orientation and never meets the step criteria. Every job here, F = 0 included, uses DefGrid3.
Even then the loose clusters (H6, H8) keep sliding along flat Cartesian directions under
TightOpt (the energy falls ~1e-8 Eh per cycle), so the jobs use ORCA's normal criteria with
up to 400 cycles: ORCA then accepts a structure whose energy and gradient are well converged
although the step is not, about 1e-6 Eh (0.03 meV) from where the tight run was drifting.
"""

import numpy as np

from hclust.geometry import Geometry
from hclust.studies.environment import d_e_table, run_environments

STUDY = "field"
LABELS = ("H3 (2)", "H4 (1)", "H6 (1)", "H8 (1)")
FIELDS = (0.0, 0.005, 0.01, 0.02)  # a.u.
GRID = ("DefGrid3",)
# ORCA's normal Opt criteria (overriding the level's TightOpt), more cycles.
GEOM = "%geom\n  TolE 5e-6\n  TolRMSG 1e-4\n  TolMaxG 3e-4\n  TolRMSD 2e-3\n  TolMaxD 4e-3\n  MaxIter 400\nend"


def environments() -> dict:
    return {
        f"F{f:g}": (GRID, (GEOM,) if f == 0 else (GEOM, f"%scf\n  EField 0.0, 0.0, {f}\nend"))
        for f in FIELDS
    }


def longest_axis_along_z(g: Geometry) -> Geometry:
    """Centre the structure and rotate its largest-spread axis onto z (right-handed frame)."""
    x = g.coords - g.coords.mean(axis=0)
    if len(g) == 1:
        return Geometry(g.symbols, x)
    _, vecs = np.linalg.eigh(x.T @ x)  # ascending spread
    frame = vecs.copy()
    if np.linalg.det(frame) < 0:
        frame[:, 0] *= -1
    return Geometry(g.symbols, x @ frame)


def run(session, campaign, analyses, workers, log):
    envs = environments()
    energies, channels = run_environments(
        session, f"{STUDY}@{campaign}", analyses, LABELS, envs, workers, log, orient=longest_axis_along_z,
    )
    rows = d_e_table(energies, channels, envs)
    # H2 polarizability along the field from the relaxed energies: alpha = -2 dE / F^2
    e0 = energies.get("H2 (1)|F0")
    for f in FIELDS[1:]:
        e = energies.get(f"H2 (1)|F{f:g}")
        if e is not None and e0 is not None:
            rows.append({"state": "H2 (1)", "channel": f"alpha_zz (a.u.) at F = {f}",
                         **{name: None for name in envs}, "alpha_au": round(-2 * (e - e0) / f**2, 3)})
    return rows
