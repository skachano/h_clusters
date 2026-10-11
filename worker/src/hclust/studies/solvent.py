"""Dielectric environment (CPCM): how D_e of the ion clusters changes with ε.

Educational only: hydrogen clusters in a solvent are unphysical (Plan, Phase 8), but the
continuum shows how charge delocalization is rewarded. A charged cluster losing H2 keeps its
charge on a smaller fragment, which the dielectric stabilizes more (Born: -q²/2r (1 - 1/ε)),
so ion-molecule complexes should weaken as ε grows; neutral complexes barely change.
"""

from hclust.studies.environment import d_e_table, run_environments

STUDY = "solvent"
LABELS = (
    "H4+ (2)", "H5+ (1)", "H7+ (1)", "H9+ (1)",
    "H3- (1)", "H5- (1)", "H7- (1)", "H9- (1)", "H4 (1)",
)
EPSILON = {"gas": None, "eps2": 2.0, "eps10": 10.0, "eps80": 80.0}


def environments() -> dict:
    out = {}
    for name, eps in EPSILON.items():
        if eps is None:
            out[name] = ((), ())
        else:
            out[name] = (("CPCM",), (f"%cpcm\n  epsilon {eps}\n  refrac 1.33\nend",))
    return out


def run(session, campaign, analyses, workers, log):
    envs = environments()
    energies, channels = run_environments(session, f"{STUDY}@{campaign}", analyses, LABELS, envs, workers, log)
    return d_e_table(energies, channels, envs)
