"""The sanity anchors of doc/Plan.md 1.2, checked against a campaign's verdicts.

Reference values: H2 r_e 0.741 A, D_e 4.747 eV, D_0 4.478 eV; H2+ r_e 1.057 A, D_e 2.79 eV;
EA(H) 0.754 eV; H3+ r_e 0.873 A, D_e(H2 + H+) 4.61 eV. Tolerances allow for the finite
aug-cc-pVTZ basis (CCSD(T) is within 0.05 eV of exact for these, Plan Phase 1).
"""

from dataclasses import dataclass

from hclust.analysis.fragments import Verdict
from hclust.analysis.verdicts import StateAnalysis
from hclust.units import HARTREE_TO_EV


@dataclass(frozen=True)
class Check:
    anchor: str
    expected: str
    found: str
    ok: bool


def check_anchors(analyses: list[StateAnalysis]) -> list[Check]:
    states = {(a.state.m, a.state.charge, a.state.mult): a for a in analyses}
    ground = _ground_states(analyses)
    checks: list[Check] = []

    def add(anchor: str, expected: str, found: str, ok: bool) -> None:
        checks.append(Check(anchor, expected, found, bool(ok)))

    def d(a: StateAnalysis | None, q: str = "E") -> float | None:
        return a.d[q][0] * HARTREE_TO_EV if a and a.d.get(q) else None

    def bond(a: StateAnalysis | None) -> float | None:
        return float(a.geometry.distances()[0]) if a and a.geometry is not None else None

    h2 = states.get((2, 0, 1))
    add("H2 r_e", "0.741 ± 0.005 Å", _f(bond(h2), "Å"), _near(bond(h2), 0.741, 0.005))
    add("H2 D_e", "4.75 ± 0.06 eV", _f(d(h2), "eV"), _near(d(h2), 4.747, 0.06))
    add("H2 D_0", "4.48 ± 0.06 eV", _f(d(h2, "E0"), "eV"), _near(d(h2, "E0"), 4.478, 0.06))

    h2p = states.get((2, 1, 2))
    add("H2+ r_e", "1.06 ± 0.01 Å", _f(bond(h2p), "Å"), _near(bond(h2p), 1.057, 0.01))
    add("H2+ D_e", "2.79 ± 0.03 eV", _f(d(h2p), "eV"), _near(d(h2p), 2.79, 0.03))

    hm = states.get((1, -1, 1))
    ea = hm.detachment * HARTREE_TO_EV if hm and hm.detachment is not None else None
    add("H- bound, EA(H)", "0.754 ± 0.05 eV", _f(ea, "eV"), _near(ea, 0.754, 0.05))

    for mult in (2, 4):
        a = states.get((2, -1, mult))
        add(f"H2- ({mult}) not bound", Verdict.UNBOUND_ELECTRON.value,
            a.verdict.value if a else "missing", a is not None and a.verdict is Verdict.UNBOUND_ELECTRON)

    h3p = states.get((3, 1, 1))
    pg = h3p.point_group if h3p else None
    add("H3+ shape", "D3h, r 0.873 ± 0.005 Å", f"{pg}, {_f(bond(h3p), 'Å')}",
        pg == "D3h" and _near(bond(h3p), 0.873, 0.005))
    channel = h3p.d["E"][1] if h3p and h3p.d.get("E") else None
    add("H3+ D_e(H2 + H+)", "4.61 ± 0.1 eV", f"{_f(d(h3p), 'eV')} ({channel})",
        _near(d(h3p), 4.61, 0.1) and channel == "H2 + H+")

    h3 = states.get((3, 0, 2))
    add("H3 falls apart to H2 + H", "not bound once ZPE is included",
        f"{h3.verdict.value if h3 else 'missing'}, D_0 {_f(d(h3, 'E0'), 'eV')}",
        h3 is not None and h3.verdict is not Verdict.BOUND_WITH_ZPE)

    odd = [states.get((m, 1, 1)) for m in (5, 7, 9)]
    d_odd = [d(a) for a in odd]
    add("H5+, H7+, H9+: H3+ core + H2", "bound with ZPE, H3·H2… units",
        ", ".join(f"{a.verdict.value} {composition_of(a)}" if a else "missing" for a in odd),
        all(a and a.verdict is Verdict.BOUND_WITH_ZPE and composition_of(a).startswith("H3·")
            for a in odd))
    add("…binding decreases with shell size", "D_e(H5+) > D_e(H7+) > D_e(H9+)",
        " > ".join(_f(x, "eV") for x in d_odd),
        None not in d_odd and d_odd[0] > d_odd[1] > d_odd[2])

    separation = {n: _h_separation(ground, n) for n in range(3, 11)}
    alternates = all(
        separation[n] is not None and separation[n + 1] is not None
        and (separation[n] > separation[n + 1] if n % 2 else separation[n] < separation[n + 1])
        for n in range(3, 10)
    )
    add("Odd–even alternation of cations", "H-atom separation energy: odd n > even neighbours",
        " ".join(f"{n}:{separation[n] * HARTREE_TO_EV:.2f}" if separation[n] is not None else f"{n}:?"
                 for n in range(3, 11)), alternates)

    neutrals = [ground.get((m, 0)) for m in range(3, 11)]
    weak = [a for a in neutrals if a is not None and a.best is not None]
    add("Neutral H_m (m > 2): weak van der Waals complexes", "D_e < 0.05 eV and D_0 ≤ 0",
        f"D_e ≤ {max(d(a) for a in weak):.3f} eV, D_0 ≤ {max(d(a, 'E0') for a in weak):+.3f} eV",
        len(weak) == 8 and all(d(a) < 0.05 and d(a, "E0") <= 0 for a in weak))

    complexes = [ground.get((m, -1)) for m in (3, 5, 7, 9)]
    add("H_m- (odd m): weak H-(H2)_k complexes", "singlet ground state with an H- unit, 0 < D_e < 0.2 eV",
        ", ".join(f"{a.state.label} {composition_of(a)} {_f(d(a), 'eV')}" if a else "missing"
                  for a in complexes),
        all(a and a.state.mult == 1 and composition_of(a).endswith("·H") and 0 < d(a) < 0.2
            for a in complexes))
    # An even number of atoms leaves no way to hold the electron as H- with paired spins:
    # every state is either unbound or a trapped (metastable) high-spin structure.
    even = [a for a in analyses if a.state.charge == -1 and a.state.m % 2 == 0]
    add("H_m- (even m): no bound anion", "every state unbound_electron or metastable",
        ", ".join(f"{a.state.label} {a.verdict.value}" for a in even),
        bool(even) and all(a.verdict in (Verdict.UNBOUND_ELECTRON, Verdict.METASTABLE) for a in even))
    return checks


def composition_of(a: StateAnalysis) -> str:
    from hclust.structures import composition

    return composition(a.geometry) if a.geometry is not None else ""


def _ground_states(analyses: list[StateAnalysis]) -> dict[tuple[int, int], StateAnalysis]:
    """The lowest-energy analysed state of each species."""
    ground: dict[tuple[int, int], StateAnalysis] = {}
    for a in analyses:
        key = (a.state.m, a.state.charge)
        if a.best is not None and (key not in ground or a.best.energy < ground[key].best.energy):
            ground[key] = a
    return ground


def _h_separation(ground: dict[tuple[int, int], StateAnalysis], n: int) -> float | None:
    """E(H_(n-1)+) + E(H) - E(H_n+), ground states (Eh)."""
    big, small, atom = ground.get((n, 1)), ground.get((n - 1, 1)), ground.get((1, 0))
    if big is None or small is None or atom is None:
        return None
    return small.best.energy + atom.best.energy - big.best.energy


def _near(x: float | None, target: float, tolerance: float) -> bool:
    return x is not None and abs(x - target) <= tolerance


def _f(x: float | None, unit: str) -> str:
    return "missing" if x is None else f"{x:.3f} {unit}"
