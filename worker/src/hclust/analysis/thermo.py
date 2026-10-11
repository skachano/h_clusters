"""Ideal-gas thermochemistry (RRHO with Grimme's quasi-RRHO entropy) at any T and p.

The conventions follow ORCA 6 so that the 298.15 K / 1 atm values reproduce ORCA's own
output (tests/test_thermo.py):
- vibrational *entropy* is quasi-RRHO: each mode interpolates between a harmonic oscillator
  and a free rotor, w = 1 / (1 + (nu0/nu)^4), nu0 = 100 cm-1 (Grimme 2012);
- vibrational *energy* stays harmonic; modes below 1 cm-1 (and imaginary ones) are dropped;
- the electronic entropy is k ln(2S+1): no low-lying excited states.

Residual: for modes below ~50 cm-1 ORCA's free-rotor entropy is ~0.03 k per mode lower than
Grimme's formula used here, so TS can differ by up to ~1.5e-4 Eh (0.1 kcal/mol) at 298 K for
the floppiest clusters. Everything else agrees to 1e-6 Eh.

All energies are in Eh. TS is reported as an energy (T times the entropy), as ORCA does.
"""

from dataclasses import dataclass

import numpy as np

from hclust.analysis.shape import is_linear, masses, principal_moments
from hclust.geometry import Geometry

# CODATA 2018
K_B = 1.380649e-23  # J/K
H_PLANCK = 6.62607015e-34  # J s
C_CM = 2.99792458e10  # cm/s
AMU = 1.66053906660e-27  # kg
HARTREE_J = 4.3597447222071e-18
ATM = 101325.0  # Pa

QRRHO_NU0_CM = 100.0
QRRHO_B_AV = 1e-44  # kg m^2, Grimme's average moment of inertia
CUTOFF_CM = 1.0


@dataclass(frozen=True)
class Thermo:
    """Corrections to the electronic energy at temperature T (K) and pressure p (atm)."""

    temperature: float
    pressure: float
    zpe: float
    thermal: float  # U - E_el - ZPE: vibrational, rotational and translational energy
    ts: float  # T * S

    @property
    def u(self) -> float:
        return self.zpe + self.thermal

    @property
    def h(self) -> float:
        return self.u + K_B * self.temperature / HARTREE_J

    @property
    def g(self) -> float:
        return self.h - self.ts


def rrho(
    geometry: Geometry | None, frequencies, mult: int, symmetry_number: int = 1,
    temperature: float = 298.15, pressure: float = 1.0,
) -> Thermo:
    """Thermochemistry of one molecule. `geometry` None means a free electron (all zero)."""
    if geometry is None:
        return Thermo(temperature, pressure, 0.0, 0.0, 0.0)
    kt = K_B * temperature  # J
    nu = np.asarray(frequencies if frequencies is not None else [], dtype=float)
    nu = nu[nu > CUTOFF_CM]
    e = H_PLANCK * C_CM * nu  # J per mode
    x = e / kt

    zpe = 0.5 * e.sum()
    e_vib = np.sum(e / np.expm1(x))
    s_vib = np.sum(_qrrho_entropy(nu, x, kt))  # in units of k

    n = len(geometry)
    if n == 1:
        e_rot, s_rot = 0.0, 0.0
    else:
        moments = principal_moments(geometry) * AMU * 1e-20  # kg m^2
        theta = H_PLANCK**2 / (8 * np.pi**2 * K_B * moments[moments > 1e-50])
        if is_linear(geometry):
            e_rot = kt
            s_rot = np.log(temperature / (symmetry_number * theta[-1])) + 1
        else:
            e_rot = 1.5 * kt
            s_rot = np.log(np.sqrt(np.pi) / symmetry_number
                           * np.sqrt(temperature**3 / np.prod(theta))) + 1.5

    mass = masses(geometry).sum() * AMU
    s_trans = np.log((2 * np.pi * mass * kt / H_PLANCK**2) ** 1.5 * kt / (pressure * ATM)) + 2.5
    e_trans = 1.5 * kt
    s_el = np.log(mult)

    return Thermo(
        temperature, pressure,
        zpe=zpe / HARTREE_J,
        thermal=(e_vib + e_rot + e_trans) / HARTREE_J,
        ts=kt * (s_vib + s_rot + s_trans + s_el) / HARTREE_J,
    )


def _qrrho_entropy(nu: np.ndarray, x: np.ndarray, kt: float) -> np.ndarray:
    """Per-mode entropy (units of k): harmonic, blended with a free rotor for low modes."""
    s_harmonic = x / np.expm1(x) - np.log1p(-np.exp(-x))
    mu = H_PLANCK / (8 * np.pi**2 * C_CM * nu)  # moment of inertia of a rotor with this frequency
    mu_eff = mu * QRRHO_B_AV / (mu + QRRHO_B_AV)
    s_rotor = 0.5 + np.log(np.sqrt(8 * np.pi**3 * mu_eff * kt / H_PLANCK**2))
    w = 1 / (1 + (QRRHO_NU0_CM / nu) ** 4)
    return w * s_harmonic + (1 - w) * s_rotor
