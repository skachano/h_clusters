"""ORCA engine: render inputs, run them in content-addressed job directories, parse results."""

import hashlib
import os
import re
import shutil
import signal
import subprocess
import threading
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path

from hclust.geometry import Geometry
from hclust.levels import Level
from hclust.parse import NORMAL_TERMINATION, parse_orca
from hclust.results import Result
from hclust.species import State

ORCA_DIR = Path(os.environ.get("ORCA_DIR", "/opt/orca"))
BASENAME = "job"
# Kept after a run; everything else (scratch, .gbw, densities) is deleted to save space.
KEEP_SUFFIXES = (".inp", ".out", ".property.json", ".property.txt", ".xyz", ".hess", ".engrad", ".opt")
# GOAT's per-worker outputs and per-iteration ensembles are deleted too.
DISCARD_MARKERS = (".goat.", ".globaliter.")
# xTB ranks H clusters wrongly, so keep a wide energy window of GOAT structures.
GOAT_BLOCK = "%goat\n  MaxEn 30\nend\n"


class Task(StrEnum):
    SP = "sp"
    OPT = "opt"
    FREQ = "freq"
    OPTFREQ = "optfreq"
    GOAT = "goat"  # global structure search (GOAT-EXPLORE), returns an ensemble

    @property
    def optimizes(self) -> bool:
        return self in (Task.OPT, Task.OPTFREQ)

    @property
    def has_freq(self) -> bool:
        return self in (Task.FREQ, Task.OPTFREQ)


@dataclass(frozen=True)
class OrcaJob:
    state: State
    geometry: Geometry
    level: Level
    task: Task = Task.SP
    maxcore_mb: int = 600
    # Retry modifiers such as "SlowConv", appended to the keyword line.
    extra_keywords: tuple[str, ...] = ()
    # Atoms (indices into geometry) that carry only basis functions: no nucleus, no electrons
    # (counterpoise corrections, Phase 8). `state` describes the real atoms.
    ghosts: tuple[int, ...] = ()
    # Extra input blocks, e.g. "%scf EField 0, 0, 0.01 end" or "%cpcm epsilon 10 end".
    blocks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.state.n_electrons == 0:
            raise ValueError("a bare proton has no electronic structure; its energy is 0")
        real = len(self.geometry) - len(set(self.ghosts))
        if real != self.state.m or set(self.geometry.symbols) != {"H"}:
            raise ValueError(f"geometry does not match {self.state.label}")
        if any(not 0 <= i < len(self.geometry) for i in self.ghosts):
            raise ValueError("ghost index out of range")

    @property
    def effective_task(self) -> Task:
        """A single atom can be neither optimized nor vibrated; H2 has one shape (no GOAT)."""
        if len(self.geometry) - len(self.ghosts) == 1:
            return Task.SP
        if self.task is Task.GOAT and len(self.geometry) < 3:
            return Task.OPT
        return self.task

    def keywords(self) -> str:
        level, state = self.level, self.state
        fallback = level.correlated and state.n_electrons < 2
        task = self.effective_task
        if task is Task.GOAT:
            return " ".join(["GOAT-EXPLORE", level.method, *self.extra_keywords])
        words = ["HF" if fallback else level.method, level.basis]
        if state.mult > 1 and level.kind != "xtb":
            words.append("UKS" if level.kind == "dft" and not fallback else "UHF")
        if task.optimizes:
            words.append(level.opt_keyword)
            if not level.analytic_gradient and not fallback:
                words.append("NumGrad")
        if task.has_freq and "NumFreq" not in self.extra_keywords:
            words.append("Freq" if level.analytic_hessian or fallback else "NumFreq")
        words.append("TightSCF")
        words.extend(self.extra_keywords)
        return " ".join(w for w in words if w)

    def render(self) -> str:
        blocks = "".join(f"{b.rstrip()}\n" for b in self.blocks)
        return (
            f"# hclust {self.state.label} {self.level.name} {self.effective_task}\n"
            f"! {self.keywords()}\n"
            f"%maxcore {self.maxcore_mb}\n"
            f"{GOAT_BLOCK if self.effective_task is Task.GOAT else ''}"
            f"{self._geom_block()}"
            f"{blocks}"
            f"* xyz {self.state.charge} {self.state.mult}\n"
            f"{self._atoms()}\n"
            "*\n"
        )

    def _atoms(self) -> str:
        """The coordinate block; ghost atoms are written 'H:' (ORCA's ghost syntax)."""
        lines = self.geometry.atom_block().split("\n")
        for i in self.ghosts:
            lines[i] = lines[i].replace("H ", "H:", 1)
        return "\n".join(lines)

    def _geom_block(self) -> str:
        if self.effective_task.optimizes and self.level.opt_max_iter:
            return f"%geom\n  MaxIter {self.level.opt_max_iter}\nend\n"
        return ""

    @property
    def hash(self) -> str:
        return job_hash(self.render(), orca_version())


def job_hash(input_text: str, version: str) -> str:
    """Content address of a job: same input + same ORCA version -> same result."""
    return hashlib.sha256(f"orca {version}\n{input_text}".encode()).hexdigest()[:16]


@cache
def orca_version() -> str:
    out = subprocess.run(
        [ORCA_DIR / "orca", "--version"], capture_output=True, text=True, timeout=60
    ).stdout
    if m := re.search(r"Program Version (\S+)", out):
        return m[1]
    raise RuntimeError(f"cannot determine ORCA version from {ORCA_DIR / 'orca'}")


def default_jobs_root() -> Path:
    return Path(os.environ.get("HCLUST_DATA", "data")) / "jobs"


def default_scratch_root() -> Path | None:
    """Where ORCA runs (big temporary files); None runs it directly in the job directory."""
    scratch = os.environ.get("HCLUST_SCRATCH")
    return Path(scratch) if scratch else None


# ORCA processes currently running (from any thread), so that they can be killed on shutdown.
_running: set[subprocess.Popen] = set()
_running_lock = threading.Lock()
_stopping = threading.Event()


def kill_all() -> None:
    """Kill every running ORCA together with its sub-programs (orca_scf, orca_mdci, ...).

    Also refuses to start new runs until allow_runs() is called, so that a thread that is
    just about to start ORCA cannot slip past the shutdown.
    """
    with _running_lock:
        _stopping.set()
        procs = list(_running)
    for proc in procs:
        _kill_group(proc)


def allow_runs() -> None:
    _stopping.clear()


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def run_orca(
    job: OrcaJob, jobs_root: Path | None = None, timeout_s: float = 3600,
    scratch_root: Path | None = None,
) -> Result:
    """Run `job` unless an identical job already terminated normally; return its parsed result.

    With a scratch root, ORCA runs in <scratch>/<hash> and only the kept files are copied
    to the job directory afterwards.
    """
    workdir = (jobs_root or default_jobs_root()) / job.hash
    out = workdir / f"{BASENAME}.out"
    is_opt = job.effective_task.optimizes
    is_goat = job.effective_task is Task.GOAT

    if out.exists() and NORMAL_TERMINATION in out.read_text(errors="replace"):
        result = parse_orca(workdir, BASENAME, is_opt, is_goat)
        result.cached = True
        return result

    workdir.mkdir(parents=True, exist_ok=True)
    for stale in workdir.iterdir():
        stale.unlink()
    scratch_root = scratch_root or default_scratch_root()
    rundir = scratch_root / job.hash if scratch_root else workdir
    if rundir != workdir:
        shutil.rmtree(rundir, ignore_errors=True)
        rundir.mkdir(parents=True)
    try:
        return _run_in(job, rundir, workdir, timeout_s, is_opt, is_goat)
    finally:
        if rundir != workdir:
            shutil.rmtree(rundir, ignore_errors=True)


def _run_in(
    job: OrcaJob, rundir: Path, workdir: Path, timeout_s: float, is_opt: bool, is_goat: bool
) -> Result:
    (rundir / f"{BASENAME}.inp").write_text(job.render())
    with (rundir / f"{BASENAME}.out").open("w") as fh:
        # ORCA must be started by its absolute path to find its sub-programs. Its own
        # session makes the whole process tree killable at once.
        proc = subprocess.Popen(
            [ORCA_DIR / "orca", f"{BASENAME}.inp"],
            cwd=rundir, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True,
        )
        with _running_lock:
            _running.add(proc)
            if _stopping.is_set():
                _kill_group(proc)
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            _kill_group(proc)
            _collect(rundir, workdir)
            return Result(
                status="failed", error=f"timeout after {timeout_s:.0f} s",
                error_kind="timeout", workdir=workdir,
            )
        finally:
            with _running_lock:
                _running.discard(proc)

    subprocess.run(
        [ORCA_DIR / "orca_2json", BASENAME, "-property"],
        cwd=rundir, capture_output=True, timeout=120,
    )
    _collect(rundir, workdir)
    return parse_orca(workdir, BASENAME, is_opt, is_goat)


def _collect(rundir: Path, workdir: Path) -> None:
    """Keep the useful outputs in the job directory; delete scratch, .gbw, densities, ..."""
    for path in rundir.iterdir():
        discard = any(marker in path.name for marker in DISCARD_MARKERS)
        if not path.is_file():
            continue
        if discard or not path.name.endswith(KEEP_SUFFIXES):
            path.unlink()
        elif rundir != workdir:
            shutil.move(path, workdir / path.name)
