"""Levels of theory of the method ladder (see doc/Plan.md, section 2)."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Level:
    name: str
    method: str
    basis: str = ""
    kind: Literal["dft", "wft"] = "dft"
    analytic_gradient: bool = True
    analytic_hessian: bool = True
    # Post-HF method that needs >= 2 electrons; one-electron systems fall back to HF.
    correlated: bool = False


LEVELS: dict[str, Level] = {
    lvl.name: lvl
    for lvl in (
        Level("L0", "r2SCAN-3c"),
        # VV10 non-local correlation has no analytic Hessian in ORCA 6.1.
        Level("L1", "wB97M-V", "def2-TZVPPD", analytic_hessian=False),
        Level("L1b", "B3LYP", "def2-TZVPPD"),
        Level(
            "L2", "CCSD(T)", "aug-cc-pVTZ", kind="wft", correlated=True,
            analytic_gradient=False, analytic_hessian=False,
        ),
    )
}
