"""VPT2: formulas against exact diagonalization of model potentials, modes against ORCA."""

from itertools import combinations_with_replacement, permutations

import numpy as np
import pytest

from hclust.analysis.shape import masses
from hclust.analysis.vpt2 import normal_modes, vpt2
from hclust.parse import parse_orca


def symmetric(entries: dict[tuple, float], n: int, rank: int) -> np.ndarray:
    t = np.zeros((n,) * rank)
    for idx, v in entries.items():
        for p in set(permutations(idx)):
            t[p] = v
    return t


def exact_zpe(omega, cubic, quartic, nb=24) -> float:
    """Lowest eigenvalue of sum w/2 (p^2 + q^2) + V3 + V4 in a product oscillator basis."""
    n = len(omega)
    big = nb + 6
    a = np.diag(np.sqrt(np.arange(1, big)), 1)
    q_big = (a + a.T) / np.sqrt(2)
    q = q_big[:nb, :nb]
    qk = {k: np.linalg.matrix_power(q_big, k)[:nb, :nb] for k in (1, 2, 3, 4)}
    eye = np.eye(nb)

    def op(powers: dict[int, int]) -> np.ndarray:
        mats = [qk[powers[i]] if powers.get(i) else eye for i in range(n)]
        out = mats[0]
        for m in mats[1:]:
            out = np.kron(out, m)
        return out

    h = np.zeros((nb**n, nb**n))
    for i, w in enumerate(omega):
        diag = np.diag(np.arange(nb) + 0.5) * w
        mats = [diag if j == i else eye for j in range(n)]
        out = mats[0]
        for m in mats[1:]:
            out = np.kron(out, m)
        h += out
    for idx in combinations_with_replacement(range(n), 3):
        if cubic[idx]:
            powers = {i: idx.count(i) for i in set(idx)}
            h += cubic[idx] * len(set(permutations(idx))) / 6 * op(powers)
    for idx in combinations_with_replacement(range(n), 4):
        if quartic[idx]:
            powers = {i: idx.count(i) for i in set(idx)}
            h += quartic[idx] * len(set(permutations(idx))) / 24 * op(powers)
    del q
    return float(np.linalg.eigvalsh(h)[0])


MODELS = {
    "two modes": (
        [1000.0, 1700.0],
        {(0, 0, 0): -220.0, (0, 0, 1): 140.0, (0, 1, 1): -90.0, (1, 1, 1): 260.0},
        {(0, 0, 0, 0): 60.0, (1, 1, 1, 1): 80.0, (0, 0, 1, 1): -40.0},
        24,
    ),
    "three modes": (
        [900.0, 1500.0, 2900.0],
        {(0, 0, 0): -150.0, (0, 1, 2): 180.0, (0, 0, 2): 90.0, (1, 1, 2): -120.0, (2, 2, 2): 200.0},
        {(0, 0, 0, 0): 40.0, (1, 1, 1, 1): 50.0, (2, 2, 2, 2): 70.0, (0, 0, 1, 1): -20.0, (1, 1, 2, 2): 25.0},
        14,
    ),
}


@pytest.mark.parametrize("name", MODELS)
def test_vpt2_zpe_error_falls_as_lambda_to_the_fourth(name):
    """VPT2 is exact through second order: halving the anharmonicity cuts its error 16-fold.
    A wrong G0 or chi term would leave a lambda^2 error (a ratio of 4)."""
    omega, f3, f4, nb = MODELS[name]
    n = len(omega)
    errors = []
    for lam in (1.0, 0.5):
        cubic = symmetric({k: v * lam for k, v in f3.items()}, n, 3)
        quartic = symmetric({k: v * lam**2 for k, v in f4.items()}, n, 4)
        approx = vpt2(omega, cubic, quartic).zpe
        errors.append(approx - exact_zpe(omega, cubic, quartic, nb))
    assert abs(errors[0]) < 2.0  # cm-1, for anharmonic corrections of tens of cm-1
    assert 10 < errors[0] / errors[1] < 25


def test_normal_modes_and_rotational_constants_match_orca(orca_fixture):
    r = parse_orca(orca_fixture("h3p_optfreq_rimp2"), is_opt=True)
    modes = normal_modes(r.geometry.symbols, r.geometry.coords, r.hessian, masses(r.geometry))
    assert modes.omega == pytest.approx([2809.80, 2809.81, 3474.68], abs=0.05)
    b, zeta = modes.rotational_constants_and_zeta()
    assert sorted(b) == pytest.approx([22.052034, 44.103990, 44.104148], rel=1e-4)  # ORCA's print
    # Coriolis sum rule: sum over modes of zeta^2 for an axis = 1 - (rotation weight), bounded
    assert np.all(np.abs(zeta) <= 1 + 1e-9)
    assert np.allclose(zeta, -np.transpose(zeta, (0, 2, 1)))
