"""Levels of theory of the method ladder (see doc/Plan.md, section 2)."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Level:
    name: str
    method: str
    basis: str = ""
    kind: Literal["xtb", "dft", "wft"] = "dft"
    analytic_gradient: bool = True
    analytic_hessian: bool = True
    # Post-HF method that needs >= 2 electrons; one-electron systems fall back to HF.
    correlated: bool = False


LEVELS: dict[str, Level] = {
    lvl.name: lvl
    for lvl in (
        # Geometry generator only (GOAT); GFN2-xTB ranks H clusters wrongly (Plan, Phase 0).
        Level("XTB", "XTB", kind="xtb"),
        Level("L0", "r2SCAN-3c"),
        # VV10 non-local correlation has no analytic Hessian in ORCA 6.1.
        Level("L1", "wB97M-V", "def2-TZVPPD", analytic_hessian=False),
        Level("L1b", "B3LYP", "def2-TZVPPD"),
        # No self-interaction or delocalization error: DFT (L0, L1) turns H5+ into the
        # proton-shared D2d structure, MP2 keeps the C2v H3+.H2 minimum (Plan, Phase 3).
        Level("L1M", "MP2", "aug-cc-pVTZ", kind="wft", correlated=True, analytic_hessian=False),
        Level(
            "L2", "CCSD(T)", "aug-cc-pVTZ", kind="wft", correlated=True,
            analytic_gradient=False, analytic_hessian=False,
        ),
    )
}
