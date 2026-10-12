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
TS_CONVERGED = "THE TS OPTIMIZATION HAS CONVERGED"
NEB_CONVERGED = "THE NEB OPTIMIZATION HAS CONVERGED"
SCF_NOT_CONVERGED = "SCF NOT CONVERGED"
# The coupled-perturbed SCF of an analytic Hessian failed (the optimization itself is done).
CPSCF_FAILED = ("CP-SCF Solver", "error termination in SCF RESPONSE")

_VERSION = re.compile(r"Program Version (\S+)")
_S2 = re.compile(r"Expectation value of <S\*\*2>\s*:\s*(-?\d+\.\d+)")
_POINT_GROUP = re.compile(r"Point Group:\s*(\S+),\s*Symmetry Number:\s*(\d+)")
_ORBITAL_ROW = re.compile(r"^\s*\d+\s+(\d+\.\d+)\s+(-?\d+\.\d+)\s+-?\d+\.\d+\s*$")
_LOEWDIN_ATOM = re.compile(r"^\s*(\d+)\s+\w+\s*:\s*(-?\d+\.\d+)(?:\s+(-?\d+\.\d+))?\s*$")
_MAYER_ATOM = re.compile(r"^\s*(\d+)\s+\w+" + r"\s+(-?\d+\.\d+)" * 6 + r"\s*$")
_BOND = re.compile(r"B\(\s*(\d+)-\w+\s*,\s*(\d+)-\w+\s*\)\s*:\s*(-?\d+\.\d+)")
# Most specific first: "Error (ORCA_MDCI): ...", then any line starting with "Error".
_ERRORS = (re.compile(r"\bError \(.*"), re.compile(r"^Error\b.*"))


def parse_orca(
    workdir: Path, basename: str = "job", is_opt: bool = False, is_goat: bool = False,
    is_neb: bool = False,
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
    if is_neb:
        return _neb_result(workdir, basename, out, props)
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
        result.opt_converged = OPT_CONVERGED in out or TS_CONVERGED in out
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


def _neb_result(workdir: Path, basename: str, out: str, props: dict) -> Result:
    """An NEB run: the minimum-energy path, start to end, and its climbing image.

    ORCA writes no per-geometry properties for NEB, so the energy and geometry come from
    the converged climbing image, or the highest image of the path without one.
    """
    path, energies = _frames(workdir / f"{basename}_MEP_trj.xyz")
    climbing = _frames(workdir / f"{basename}_NEB-CI_converged.xyz")
    if climbing[0]:
        geometry, energy = climbing[0][0], climbing[1][0]
    elif path:
        top = max(range(len(energies)), key=energies.__getitem__)
        geometry, energy = path[top], energies[top]
    else:
        return Result(status="failed", error="NEB wrote no path", error_kind="other", workdir=workdir)
    result = Result(
        status="ok", energy=energy, geometry=geometry, path=path, path_energies=energies,
        orca_version=_VERSION.search(out)[1],
        wall_time_s=props.get("Calculation_Timings", {}).get("SUM"), workdir=workdir,
    )
    result.opt_converged = NEB_CONVERGED in out
    if not result.opt_converged:
        result.status, result.error_kind = "failed", "opt"
        result.error = "NEB did not converge"
    if s2 := _S2.findall(out):
        result.s2 = float(s2[-1])
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


def _frames(path: Path) -> tuple[list[Geometry], list[float]]:
    """Multi-frame XYZ written by NEB, in file order; comments end in 'E <energy in Eh>'."""
    if not path.exists():
        return [], []
    lines = path.read_text().splitlines()
    geometries, energies, i = [], [], 0
    while i < len(lines) and lines[i].strip():
        n = int(lines[i])
        frame = Geometry.from_xyz("\n".join(lines[i : i + n + 2]))
        energies.append(float(frame.comment.split()[-1]))
        geometries.append(Geometry(frame.symbols, frame.coords))
        i += n + 2
    return geometries, energies


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
    result.hessian = np.array(entry["Hessian"]["HESSIAN"], dtype=float)
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


def bond_orders(out: str) -> dict[str, list[tuple[int, int, float]]]:
    """Löwdin and Mayer bond orders (atom i < j, 0-based) from the last blocks of an output.

    ORCA prints only orders above a threshold: set MAYER_BONDORDERTHRESH and
    LOEWDIN_BONDORDERTHRESH in %method, and Print[P_BondOrder_L] 1 in %output for Löwdin.
    """
    found = {}
    for kind, header in (("loewdin", "LOEWDIN BOND ORDERS"), ("mayer", "Mayer bond orders larger than")):
        start = out.rfind(header)
        if start < 0:
            continue
        lines = out[start:].splitlines()[1:]
        pairs = []
        for line in lines:
            if set(line.strip()) <= {"-"} and not pairs:
                continue  # the underline below the header, or a blank line before the rows
            if not line.strip():
                break
            pairs.extend((int(i), int(j), float(v)) for i, j, v in _BOND.findall(line))
        found[kind] = sorted((min(i, j), max(i, j), v) for i, j, v in pairs)
    return found


def printed_matrix(out: str, title: str) -> np.ndarray | None:
    """A square matrix printed by ORCA (%output Print[P_Overlap], Print[P_Density], ...).

    The last block titled exactly `title` (a line of its own, underlined with dashes), in
    column groups of six: a header line of column indices, then one row per basis function.
    """
    lines = out.splitlines()
    starts = [k for k in range(len(lines) - 1)
              if lines[k].strip() == title and set(lines[k + 1].strip()) == {"-"}]
    if not starts:
        return None
    columns: list[int] = []
    entries: dict[tuple[int, int], float] = {}
    for line in lines[starts[-1] + 2:]:
        tokens = line.split()
        if tokens and all(t.isdigit() for t in tokens):
            columns = [int(t) for t in tokens]
        elif tokens and tokens[0].isdigit() and len(tokens) == len(columns) + 1:
            row = int(tokens[0])
            for c, v in zip(columns, tokens[1:]):
                entries[row, c] = float(v)
        elif entries:
            break
    if not entries:
        return None
    n = max(max(k) for k in entries) + 1
    matrix = np.zeros((n, n))
    for (i, j), v in entries.items():
        matrix[i, j] = v
    return matrix


def atom_populations(out: str) -> list[dict] | None:
    """Per atom: Löwdin charge and spin population (None for closed shells), and Mayer's
    total valence VA and free valence FA, from the last population analysis of an output."""
    lines = out.splitlines()
    heads = [k for k, line in enumerate(lines)
             if line.strip() in ("LOEWDIN ATOMIC CHARGES", "LOEWDIN ATOMIC CHARGES AND SPIN POPULATIONS")]
    if not heads:
        return None
    atoms: list[dict] = []
    for line in lines[heads[-1] + 2:]:
        m = _LOEWDIN_ATOM.match(line)
        if not m:
            break
        atoms.append({"charge": float(m[2]), "spin": float(m[3]) if m[3] else None,
                      "valence": None, "free_valence": None})
    heads = [k for k, line in enumerate(lines) if line.split()[:7] == ["ATOM", "NA", "ZA", "QA", "VA", "BVA", "FA"]]
    if heads:
        for line in lines[heads[-1] + 1:]:
            m = _MAYER_ATOM.match(line)
            if not m:
                break
            i = int(m[1])
            if i < len(atoms):
                atoms[i]["valence"], atoms[i]["free_valence"] = float(m[5]), float(m[7])
    return atoms or None

