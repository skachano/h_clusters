"""Levels of theory of the method ladder (see doc/Plan.md, section 2)."""

from dataclasses import dataclass
from typing import Literal

from hclust.units import HARTREE_TO_EV


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
    # Scratch disk (GB) one job needs at m = 10; scaled as (m/10)^4 by the scheduler.
    scratch_gb_m10: float = 0.5
    # Optimizer convergence keyword and cycle limit (None: ORCA's default of 50).
    opt_keyword: str = "TightOpt"
    opt_max_iter: int | None = None
    # An anion whose HOMO lies above this (eV) does not hold its extra electron: it sits in
    # the most diffuse basis functions, near +1 eV in aug-cc-pVTZ and def2-TZVPPD, while bound
    # anions (H-) lie below +0.2 eV (Plan, Phase 4). None: the level cannot tell (no diffuse
    # functions or a large self-interaction error put even H- above +4 eV).
    unbound_homo_ev: float | None = None

    def anion_unbound(self, homo: float | None, charge: int) -> bool | None:
        """Whether an anion's extra electron is unbound; None when unknown or not an anion."""
        if charge >= 0 or homo is None or self.unbound_homo_ev is None:
            return None
        return homo * HARTREE_TO_EV > self.unbound_homo_ev


LEVELS: dict[str, Level] = {
    lvl.name: lvl
    for lvl in (
        # Geometry generator only (GOAT); GFN2-xTB ranks H clusters wrongly (Plan, Phase 0).
        Level("XTB", "XTB", kind="xtb"),
        # Screening only: H2 units sliding on flat surfaces need more than 3 x 50 TightOpt
        # cycles (H7+, Plan Phase 4); L1/L1M re-optimize tightly anyway.
        Level("L0", "r2SCAN-3c", opt_keyword="Opt", opt_max_iter=150),
        # Analytic Hessian: ~16 min for H10 opt+freq, vs ~2 h for wB97M-V (Plan, Phase 4).
        # 150 cycles: floppy m >= 7 clusters exceed 3 x 50 TightOpt cycles (Plan, Phase 4).
        Level("L1", "wB97X-D4", "def2-TZVPPD", opt_max_iter=150, unbound_homo_ev=0.5),
        # VV10 non-local correlation has no analytic Hessian in ORCA 6.1.
        Level("L1V", "wB97M-V", "def2-TZVPPD", analytic_hessian=False, unbound_homo_ev=0.5),
        Level("L1b", "B3LYP", "def2-TZVPPD"),
        # No self-interaction or delocalization error: DFT (L0, L1) turns H5+ into the
        # proton-shared D2d structure, MP2/aVTZ keeps the C2v H3+.H2 minimum (Plan, Phase 3).
        # RI + RI-JK: 38 s per H10 gradient instead of 200 s. No analytic MP2 Hessian.
        Level(
            "L1M", "RI-MP2 RIJK", "aug-cc-pVTZ aug-cc-pVTZ/C aug-cc-pVTZ/JK", kind="wft",
            correlated=True, analytic_hessian=False, scratch_gb_m10=2, opt_max_iter=150,
            unbound_homo_ev=0.5,
        ),
        Level(
            "L2", "CCSD(T)", "aug-cc-pVTZ", kind="wft", correlated=True,
            analytic_gradient=False, analytic_hessian=False, scratch_gb_m10=12.5,
            unbound_homo_ev=0.5,  # HOMO of the HF reference
        ),
        # Basis-set limit (Phase 8): ORCA runs aVTZ and aVQZ and extrapolates (SCF exponential,
        # correlation 1/X^3). aVQZ needs ~16x the aVTZ scratch, so only small clusters.
        Level(
            "L4", "CCSD(T)", "Extrapolate(3/4,aug-cc)", kind="wft", correlated=True,
            analytic_gradient=False, analytic_hessian=False, scratch_gb_m10=200,
        ),
    )
}
