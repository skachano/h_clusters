"""Running a study's jobs: thread pool, dedup by hash, one SCF retry, results in the DB."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace

from sqlmodel import Session, select

from hclust.db import StudyResult, _now
from hclust.engines.orca import OrcaJob, allow_runs, kill_all, run_orca
from hclust.results import Result

SCF_RETRY = ("SlowConv",)


def run_jobs(
    session: Session, study: str, jobs: dict[str, OrcaJob], workers: int = 8,
    timeout_s: float = 6 * 3600, log: Callable[[str], None] = print,
    data: Callable[[str, Result], dict | None] | None = None,
) -> dict[str, Result]:
    """Run every job not already stored with the same hash; return all results by key.

    `data(key, result)` picks study-specific details to keep in the row (frequencies, ...);
    rows already stored get it recomputed from the kept outputs, so analysis changes need no
    new ORCA runs.
    """
    stored = {r.key: r for r in session.exec(select(StudyResult).where(StudyResult.study == study))}
    todo = {k: j for k, j in jobs.items() if not (k in stored and stored[k].hash == j.hash and stored[k].status == "ok")}
    by_hash: dict[str, list[str]] = {}
    for k, j in todo.items():
        by_hash.setdefault(j.hash, []).append(k)
    log(f"{study}: {len(jobs)} jobs, {len(jobs) - len(todo)} already done, {len(by_hash)} to run")

    results: dict[str, Result] = {}
    allow_runs()
    pool = ThreadPoolExecutor(max_workers=workers)
    futures = {pool.submit(_run_one, todo[keys[0]], timeout_s): keys for keys in by_hash.values()}
    try:
        for n, future in enumerate(as_completed(futures), 1):
            keys = futures[future]
            ran, result = future.result()
            for k in keys:
                results[k] = result
                details = (data(k, result) if data and result.ok else None) or {}
                if ran.hash != todo[k].hash:
                    details["run_hash"] = ran.hash  # after an SCF retry
                _store(session, study, k, todo[k], result, details or None)
            session.commit()
            state = "ok" if result.ok else f"failed: {result.error}"
            log(f"  [{n}/{len(futures)}] {keys[0]}{f' (+{len(keys) - 1})' if len(keys) > 1 else ''} {state}"
                f"{' (cached)' if result.cached else f' ({result.wall_time_s or 0:.0f} s)'}")
    except KeyboardInterrupt:
        kill_all()
        pool.shutdown(wait=True, cancel_futures=True)
        raise
    pool.shutdown()
    refreshed = False
    for k in jobs.keys() - results.keys():  # already stored: re-read the kept ORCA files
        results[k] = run_orca(jobs[k], timeout_s=timeout_s)
        if data and results[k].ok:
            details = {**(stored[k].data or {}), **(data(k, results[k]) or {})}
            if details != (stored[k].data or {}):
                stored[k].data, refreshed = details, True
                session.add(stored[k])
    if refreshed:
        session.commit()
    return results


def stored_rows(session: Session, study: str) -> dict[str, StudyResult]:
    return {r.key: r for r in session.exec(select(StudyResult).where(StudyResult.study == study))}


def _run_one(job: OrcaJob, timeout_s: float) -> tuple[OrcaJob, Result]:
    try:
        result = run_orca(job, timeout_s=timeout_s)
        if not result.ok and result.error_kind == "scf":
            job = replace(job, extra_keywords=job.extra_keywords + SCF_RETRY)
            result = run_orca(job, timeout_s=timeout_s)
        return job, result
    except Exception as e:  # one broken job must not stop the study
        return job, Result(status="failed", error=f"{type(e).__name__}: {e}", error_kind="other")


def _store(session: Session, study: str, key: str, job: OrcaJob, result: Result, data: dict | None) -> None:
    """`job` is the job as requested, so its hash matches on the next run even after a retry."""
    row = session.exec(select(StudyResult).where(StudyResult.study == study, StudyResult.key == key)).first()
    row = row or StudyResult(study=study, key=key, hash=job.hash, status="")
    row.hash, row.status, row.energy = job.hash, "ok" if result.ok else "failed", result.energy
    row.error, row.wall_s, row.data, row.updated_at = result.error, result.wall_time_s, data, _now()
    session.add(row)
