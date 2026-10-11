"""Parse ORCA 6 outputs: `<base>.property.json` (from orca_2json) plus a few text-only items."""

import json
import re
from pathlib import Path

import numpy as np

from hclust.geometry import Geometry
from hclust.results import Result
from hclust.units import BOHR_TO_ANGSTROM

NORMAL_TERMINATION = "ORCA TERMINATED NORMALLY"
OPT_CONVERGED = "THE OPTIMIZATION HAS CONVERGED"
SCF_NOT_CONVERGED = "SCF NOT CONVERGED"
# The coupled-perturbed SCF of an analytic Hessian failed (the optimization itself is done).
CPSCF_FAILED = ("CP-SCF Solver", "error termination in SCF RESPONSE")

_VERSION = re.compile(r"Program Version (\S+)")
_S2 = re.compile(r"Expectation value of <S\*\*2>\s*:\s*(-?\d+\.\d+)")
_POINT_GROUP = re.compile(r"Point Group:\s*(\S+),\s*Symmetry Number:\s*(\d+)")
_ORBITAL_ROW = re.compile(r"^\s*\d+\s+(\d+\.\d+)\s+(-?\d+\.\d+)\s+-?\d+\.\d+\s*$")
# Most specific first: "Error (ORCA_MDCI): ...", then any line starting with "Error".
_ERRORS = (re.compile(r"\bError \(.*"), re.compile(r"^Error\b.*"))


def parse_orca(
    workdir: Path, basename: str = "job", is_opt: bool = False, is_goat: bool = False
) -> Result:
    workdir = Path(workdir)
    out_path = workdir / f"{basename}.out"
    out = out_path.read_text(errors="replace") if out_path.exists() else ""

    if NORMAL_TERMINATION not in out:
        if SCF_NOT_CONVERGED in out:
            kind = "scf"
        elif any(marker in out for marker in CPSCF_FAILED):
            kind = "cpscf"
        else:
            kind = "other"
        return Result(
            status="failed", error=_error_message(out), error_kind=kind,
            geometry=_last_geometry(workdir / f"{basename}.property.json"), workdir=workdir,
        )

    props = json.loads((workdir / f"{basename}.property.json").read_text())
    last = props["Geometries"][-1]

    result = Result(
        status="ok",
        energy=last["Single_Point_Data"]["FinalEnergy"],
        geometry=_geometry(last),
        mulliken_charges=_charges(last),
        orca_version=_VERSION.search(out)[1],
        wall_time_s=props.get("Calculation_Timings", {}).get("SUM"),
        workdir=workdir,
    )
    if is_goat:
        result.ensemble, result.ensemble_energies = _ensemble(workdir / f"{basename}.finalensemble.xyz")
        result.geometry, result.energy = result.ensemble[0], result.ensemble_energies[0]
    elif is_opt:
        result.opt_converged = OPT_CONVERGED in out
        if not result.opt_converged:
            result.status, result.error_kind = "failed", "opt"
            result.error = "geometry optimization did not converge"

    if s2 := _S2.findall(out):
        result.s2 = float(s2[-1])
    result.homo, result.lumo = _frontier_orbitals(out)

    if "THERMOCHEMISTRY_Energies" in last:
        _add_vibrations(result, last, len(result.geometry))
    if pg := _POINT_GROUP.findall(out):
        result.point_group, sym = pg[-1]
        result.symmetry_number = int(sym)
    return result


def _last_geometry(path: Path) -> Geometry | None:
    """The last geometry a failed run wrote, if any (a restart point)."""
    try:
        return _geometry(json.loads(path.read_text())["Geometries"][-1])
    except (OSError, ValueError, KeyError, IndexError):
        return None


def _geometry(entry: dict) -> Geometry:
    coords = entry["Geometry"]["Coordinates"]
    rows = coords["Cartesians"]
    xyz = np.array([r[1:4] for r in rows], dtype=float)
    if coords["Units"] == "a.u.":
        xyz *= BOHR_TO_ANGSTROM
    return Geometry(tuple(r[0] for r in rows), xyz)


def _ensemble(path: Path) -> tuple[list[Geometry], list[float]]:
    """Multi-frame XYZ written by GOAT; each comment line starts with the energy (Eh)."""
    lines = path.read_text().splitlines()
    geometries, energies, i = [], [], 0
    while i < len(lines) and lines[i].strip():
        n = int(lines[i])
        frame = Geometry.from_xyz("\n".join(lines[i : i + n + 2]))
        energies.append(float(frame.comment.split()[0]))
        geometries.append(Geometry(frame.symbols, frame.coords))
        i += n + 2
    order = sorted(range(len(energies)), key=energies.__getitem__)
    return [geometries[k] for k in order], [energies[k] for k in order]


def _charges(entry: dict) -> list[float] | None:
    pops = entry.get("Mulliken_Population_Analysis")
    if not pops:
        return None
    return [q[0] for q in pops[0]["AtomicCharges"]]


def _add_vibrations(result: Result, entry: dict, n_atoms: int) -> None:
    thermo = entry["THERMOCHEMISTRY_Energies"][-1]
    n_zero = 5 if thermo["isLinear"] else 6
    freqs = np.array([f[0] for f in thermo["FREQ"]])
    result.frequencies = freqs[n_zero:]
    result.thermo = {
        key: thermo[key]
        for key in ("temperature", "pressure", "elEnergy", "zpe", "innerEnergyU",
                    "enthalpyH", "entropyS", "freeEnergyG")
    }
    # MODES is (3N, 3N) with one normal mode per column, like the .hess file.
    modes = np.array(entry["Hessian"]["MODES"], dtype=float)
    result.modes = modes[:, n_zero:].T.reshape(-1, n_atoms, 3)


def _frontier_orbitals(out: str) -> tuple[float | None, float | None]:
    """HOMO/LUMO (Eh) from the last ORBITAL ENERGIES block, over both spins for UHF."""
    start = out.rfind("ORBITAL ENERGIES")
    if start < 0:
        return None, None
    occupied, virtual = [], []
    for line in out[start:].splitlines()[1:]:
        if "POPULATION ANALYSIS" in line or line.startswith("*"):
            break
        if m := _ORBITAL_ROW.match(line):
            occ, energy = float(m[1]), float(m[2])
            (occupied if occ > 0 else virtual).append(energy)
    return (max(occupied) if occupied else None, min(virtual) if virtual else None)


def _error_message(out: str) -> str:
    if not out:
        return "no output"
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    for pattern in _ERRORS:
        for line in lines:
            if m := pattern.search(line):
                return m[0]
    return lines[-1]
