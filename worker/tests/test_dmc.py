"""Diffusion Monte Carlo and the pair potential against exactly solvable cases."""

import numpy as np
import pytest

from hclust.analysis.dmc import MASS_H2, PairPotential, block_error, dmc, radial_ground_state


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
