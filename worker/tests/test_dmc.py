"""Diffusion Monte Carlo and the pair potential against exactly solvable cases."""

import numpy as np
import pytest

from hclust.analysis.dmc import (
    MASS_H, MASS_H2, PairPotential, block_error, coupled_channel_ground_state, dmc,
    IonThreeBody, ion_rotor_anisotropy, radial_ground_state,
)


def morse(d, a, re):
    return lambda r: d * (np.exp(-2 * a * (np.asarray(r) - re)) - 2 * np.exp(-a * (np.asarray(r) - re)))


def test_pair_potential_interpolates_and_extrapolates():
    exact = morse(1e-4, 1.0, 6.5)
    # the spacing of the real scans (studies/dmc.py): 0.1 Å on the wall and in the well, then wider
    r = np.concatenate([np.arange(4.5, 8.7, 0.19), np.linspace(9, 16, 8)])
    pot = PairPotential(r, exact(r))
    assert np.allclose(pot(r), exact(r), atol=1e-12)
    mid = np.linspace(5, 15, 101)
    well = exact(mid) < 2e-4  # where the walkers live: within ~1e-6 Eh of the true curve
    assert np.allclose(pot(mid)[well], exact(mid)[well], atol=1e-6)
    assert np.allclose(pot(mid)[~well], exact(mid)[~well], rtol=0.02)  # the steep wall: 2 %
    assert pot(np.array([4.0]))[0] > pot(np.array([4.5]))[0] > 0  # wall keeps rising
    # a pure -C6/R^6 tail is recovered beyond the grid
    tail = PairPotential(np.linspace(4, 12, 30), np.where(np.linspace(4, 12, 30) < 5, 1e-3 * np.exp(-(np.linspace(4, 12, 30) - 4)), -12 / np.linspace(4, 12, 30) ** 6))
    assert tail.tail[0] == pytest.approx(12, rel=1e-6)
    assert tail(np.array([20.0]))[0] == pytest.approx(-12 / 20 ** 6, rel=1e-6)


def test_radial_solver_gives_the_3d_harmonic_oscillator():
    mu, omega = 1000.0, 1e-3
    e, _ = radial_ground_state(lambda r: 0.5 * mu * omega**2 * r**2, mu, r_min=0.0, r_max=8.0, n=2000)
    assert e == pytest.approx(1.5 * omega, rel=1e-4)


def test_dmc_gives_the_3d_harmonic_oscillator():
    # two particles bound by a spring: relative motion is a 3D oscillator, E0 = 3/2 omega
    m, k = 2000.0, 1e-3
    mu = m / 2
    omega = np.sqrt(k / mu)
    res = dmc([m, m], {(0, 1): lambda r: 0.5 * k * r**2}, np.array([[0, 0, 0], [0, 0, 1.0]]),
              walkers=1000, dt=5.0, steps=6000, equilibration=2000, seed=1)
    assert res.energy == pytest.approx(1.5 * omega, abs=4 * res.error + 0.01 * omega)
    assert res.size_growth == pytest.approx(1, abs=0.1)


def test_dmc_agrees_with_the_exact_dimer_level():
    # an H2-H2-like well, deep enough for one clear bound state
    pot = morse(1.2e-4, 0.9, 6.5)
    mu = MASS_H2 / 2
    exact, mean_r = radial_ground_state(pot, mu, r_min=3.0, r_max=60, n=2500)
    assert exact < 0
    res = dmc([MASS_H2, MASS_H2], {(0, 1): pot}, np.array([[0, 0, 0], [0, 0, 6.5]]),
              walkers=2000, dt=20.0, steps=15000, equilibration=5000, seed=2)
    assert res.energy == pytest.approx(exact, abs=max(4 * res.error, 0.03 * abs(exact)))


def test_dmc_sees_an_unbound_pair_fall_apart():
    pot = morse(1e-6, 0.9, 6.5)  # far too shallow for a bound state
    mu = MASS_H2 / 2
    exact, _ = radial_ground_state(pot, mu, r_min=3.0, r_max=60, n=2500)
    assert exact > -1e-8  # nothing bound (the box gives a small positive level)
    res = dmc([MASS_H2, MASS_H2], {(0, 1): pot}, np.array([[0, 0, 0], [0, 0, 6.5]]),
              walkers=1000, dt=20.0, steps=8000, equilibration=2000, seed=3)
    assert res.size_growth > 1.2  # the walkers keep spreading
    assert res.energy > -5e-7


def test_block_error_of_white_noise():
    x = np.random.default_rng(0).standard_normal(100000)
    assert block_error(x) == pytest.approx(1 / np.sqrt(len(x)), rel=0.4)


def test_tridiagonal_solver_matches_dense_diagonalization():
    pot = morse(1.2e-4, 0.9, 6.5)
    mu, r_min, r_max, n = MASS_H2 / 2, 3.0, 40.0, 1500
    e, mean_r = radial_ground_state(pot, mu, r_min=r_min, r_max=r_max, n=n)
    r = np.linspace(r_min, r_max, n + 2)[1:-1]
    k = 1 / (2 * mu * (r[1] - r[0]) ** 2)
    dense = np.diag(2 * k + pot(r)) - k * (np.eye(n, k=1) + np.eye(n, k=-1))
    w, v = np.linalg.eigh(dense)
    assert e == pytest.approx(w[0], rel=1e-9)
    assert mean_r == pytest.approx(np.sum(r * v[:, 0] ** 2), rel=1e-6)


def test_pair_potential_ion_tail():
    r = np.linspace(4, 20, 40)
    v = np.where(r < 5, 1e-3 * np.exp(-(r - 4)), -2.7 / r ** 4 - 30 / r ** 6)
    pot = PairPotential(r, v, tail_powers=(4, 6))
    assert pot.tail[0] == pytest.approx(2.7, rel=1e-6)
    assert pot(np.array([40.0]))[0] == pytest.approx(-2.7 / 40 ** 4 - 30 / 40 ** 6, rel=1e-6)


def test_coupled_channels_reduce_to_the_radial_equation():
    pot = morse(1.2e-3, 0.9, 6.0)
    mu = MASS_H2 * 2 / 3
    exact, _ = radial_ground_state(pot, mu, r_min=3.0, r_max=60, n=20000)
    e, weights = coupled_channel_ground_state({0: pot}, mu, r_min=3.0, r_max=60, n=500)
    assert e == pytest.approx(exact, rel=1e-4)
    assert weights[0] == pytest.approx(1)


def test_anisotropy_only_adds_binding():
    # the isotropic average is variational: any P2 term lowers the level and mixes in j = 2
    pot = morse(1.2e-3, 0.9, 6.0)
    mu = MASS_H2 * 2 / 3
    e0, _ = coupled_channel_ground_state({0: pot}, mu)
    e, weights = coupled_channel_ground_state({0: pot, 2: lambda r: 0.3 * pot(r)}, mu)
    assert e < e0
    assert 0.99 < weights[0] < 1 and weights[2] > 0
    # converged in the rotor basis and the radial grid
    assert coupled_channel_ground_state({0: pot, 2: lambda r: 0.3 * pot(r)}, mu, j_max=12, n=700)[0] == pytest.approx(e, rel=1e-8)


def test_ion_three_body_recovers_its_orientation_model():
    # tables made from known a, b, d (smooth in R and cos theta); any orientation is reproduced
    r = np.linspace(5.0, 9.0, 9)
    c = np.linspace(-1.0, 0.5, 7)
    rr, cc = np.meshgrid(r, c, indexing="ij")
    a, b, d = 1e-4 * np.exp(-rr + 5) * (1 + cc), -2e-4 * np.exp(-rr + 5), 5e-5 * np.exp(-rr + 5) * cc
    end, side, mixed = a + 2 * b + d, a - b + d / 4, a + b / 2 - d / 2
    three = IonThreeBody(2, [0, 1], r, c, end, side, mixed, kappa=1.0)
    rng = np.random.default_rng(0)
    x = np.zeros((50, 3, 3))
    x[:, 0] = [0, 0, 6.0]
    t = rng.uniform(np.radians(70), np.pi, 50)
    x[:, 1, 0], x[:, 1, 2] = 6.0 * np.sin(t), 6.0 * np.cos(t)
    u = rng.standard_normal((50, 2, 3))
    u /= np.linalg.norm(u, axis=2, keepdims=True)
    p2 = [1.5 * (np.sum(-x[:, i] * u[:, i], axis=1) / 6.0) ** 2 - 0.5 for i in range(2)]
    k = dict(a=1e-4 * np.exp(-1) * (1 + np.cos(t)), b=-2e-4 * np.exp(-1), d=5e-5 * np.exp(-1) * np.cos(t))
    expected = k["a"] + k["b"] * (p2[0] + p2[1]) + k["d"] * p2[0] * p2[1]
    assert np.allclose(three(x, u), expected, rtol=1e-3, atol=1e-9)
    # u = None means both end-on; beyond the grid the term decays
    assert np.allclose(three(x, None), k["a"] + 2 * k["b"] + k["d"], rtol=1e-3, atol=1e-9)
    far = x * 11.0 / 6.0
    assert np.allclose(three(far, None), np.exp(-2.0) * three(x * 9.0 / 6.0, None), rtol=1e-9)


def test_rotor_dmc_agrees_with_coupled_channels():
    # an ion and a rotating H2 with a strong P2 term: the anisotropy nearly doubles the binding
    pot = morse(1.0e-3, 0.9, 6.5)
    v2 = lambda r: -2e-3 * np.exp(-0.6 * (np.asarray(r) - 6.5))  # noqa: E731
    mu = MASS_H2 * MASS_H / (MASS_H2 + MASS_H)
    iso, _ = coupled_channel_ground_state({0: pot}, mu)
    exact, _ = coupled_channel_ground_state({0: pot, 2: v2}, mu)
    assert exact < 1.5 * iso
    res = dmc([MASS_H2, MASS_H], {(0, 1): pot}, np.array([[0, 0, 0], [0, 0, 6.5]]), walkers=1500,
              dt=10.0, steps=15000, equilibration=5000, seed=3,
              many_body=ion_rotor_anisotropy(1, {2: v2}), rotors=1)
    assert res.energy == pytest.approx(exact, abs=max(4 * res.error, 0.02 * abs(exact)))
