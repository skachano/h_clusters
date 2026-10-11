"""Command line: python -m hclust plan|run|status."""

import signal
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Annotated

import typer
from sqlmodel import Session, select

from hclust.campaign import CampaignSpec
from hclust.db import Campaign, Candidate, Job, JobResult, JobStatus, StateRow, Structure, get_engine
from hclust.geometry import Geometry
from hclust.structures import composition
from hclust.units import HARTREE_TO_KCAL
from hclust.runner import (
    Runner, flag_unbound, plan as plan_campaign, relabel_dissociated, requeue_failed,
    reselect as reselect_campaign,
)

app = typer.Typer(no_args_is_help=True, add_completion=False)

SYMBOLS = {
    JobStatus.DONE: "✓",
    JobStatus.FAILED: "✗",
    JobStatus.RUNNING: "▶",
    JobStatus.PENDING: "·",
    JobStatus.DISSOCIATED: "÷",
}

CampaignFile = Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="campaign YAML")]


@app.command()
def plan(campaign: CampaignFile) -> None:
    """Insert the campaign's states, seeds and root jobs into the database."""
    spec = CampaignSpec.load(campaign)
    with Session(get_engine()) as session:
        plan_campaign(session, spec)
        _print_status(session, spec.name)


@app.command()
def run(
    campaign: CampaignFile,
    workers: Annotated[int | None, typer.Option(help="concurrent ORCA jobs")] = None,
) -> None:
    """Plan and run a campaign until every job has finished. Safe to interrupt and rerun."""
    spec = CampaignSpec.load(campaign)
    # `docker stop` sends SIGTERM; handle it like Ctrl-C so that jobs are requeued cleanly.
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)
    with Session(get_engine()) as session:
        runner = Runner(session, spec, workers=workers)
        try:
            counts = runner.run()
        except KeyboardInterrupt:
            sys.exit(130)
        typer.echo(f"finished: {counts}")
        _print_status(session, spec.name)


@app.command("retry-failed")
def retry_failed(
    campaign: CampaignFile,
    stage: Annotated[str | None, typer.Option(help="only this stage")] = None,
    reopen: Annotated[bool, typer.Option(help="also reopen finished selections; requeue intact 'dissociated' jobs")] = False,
) -> None:
    """Put failed jobs back in the queue (by default unless their state's selection already ran)."""
    spec = CampaignSpec.load(campaign)
    with Session(get_engine()) as session:
        requeued, skipped = requeue_failed(session, spec, stage, reopen=reopen)
    typer.echo(f"requeued {requeued} job(s); skipped {skipped} whose selection already ran")


@app.command()
def relabel(campaign: CampaignFile) -> None:
    """Mark failed jobs whose last geometry has fallen apart as 'dissociated', and flag
    results of anions that do not hold their extra electron as 'unbound'."""
    spec = CampaignSpec.load(campaign)
    with Session(get_engine()) as session:
        n = relabel_dissociated(session, spec)
        n_unbound = flag_unbound(session, spec)
    typer.echo(f"relabelled {n} failed job(s) as dissociated; {n_unbound} result(s) are unbound anions")


@app.command()
def reselect(
    campaign: CampaignFile,
    stage: Annotated[list[str] | None, typer.Option(help="select stage(s); default: all")] = None,
) -> None:
    """Forget select-stage decisions so they run again (e.g. after changing selection rules)."""
    spec = CampaignSpec.load(campaign)
    with Session(get_engine()) as session:
        n = reselect_campaign(session, spec, set(stage) if stage else None)
    typer.echo(f"cleared {n} selection record(s); they are redone on the next run")


@app.command()
def status(name: Annotated[str, typer.Argument(help="campaign name or YAML file")]) -> None:
    """Show a states × stages table of job statuses (select stages: promoted/seen)."""
    if name.endswith((".yaml", ".yml")):
        name = CampaignSpec.load(Path(name)).name
    with Session(get_engine()) as session:
        _print_status(session, name)


@app.command()
def structures(
    name: Annotated[str, typer.Argument(help="campaign name")],
    stage: Annotated[str, typer.Option(help="stage whose results to list")] = "opt",
) -> None:
    """List each state's structures from one stage, lowest energy first."""
    with Session(get_engine()) as session:
        campaign = _campaign(session, name)
        jobs = session.exec(
            select(Job).where(Job.campaign_id == campaign.id, Job.stage == stage)
        ).all()
        children = defaultdict(list)
        for job in session.exec(select(Job).where(Job.campaign_id == campaign.id)).all():
            if job.parent_id is not None:
                children[job.parent_id].append(job)
        sources = {
            c.job_id: c.source
            for c in session.exec(select(Candidate).where(Candidate.campaign_id == campaign.id))
        }
        by_state = defaultdict(list)
        for job in jobs:
            if (result := session.get(JobResult, job.id)) is not None:
                by_state[job.state_id].append((job, result))

        for state_id, rows in sorted(by_state.items(), key=lambda kv: session.get(StateRow, kv[0]).to_state()):
            typer.echo(f"\n{session.get(StateRow, state_id).to_state().label}  ({len(rows)} structures)")
            typer.echo(f"  {'job':>5} {'ΔE kcal':>8} {'imag':>4} {'units':<12} {'shortest H-H (Å)':<22} {'source':<15} children")
            e_min = min(r.energy for _, r in rows)
            for job, result in sorted(rows, key=lambda jr: jr[1].energy):
                geometry = Geometry.from_xyz(session.get(Structure, result.final_structure_id).xyz)
                shortest = " ".join(f"{d:.3f}" for d in geometry.distances()[:3])
                kids = " ".join(
                    f"{k.stage}={r.energy:.6f}" for k in children[job.id]
                    if (r := session.get(JobResult, k.id)) is not None
                )
                typer.echo(
                    f"  {job.id:>5} {(result.energy - e_min) * HARTREE_TO_KCAL:8.2f} "
                    f"{'' if result.n_imag is None else result.n_imag:>4} "
                    f"{composition(geometry) + (' e⁻' if result.unbound else ''):<12} "
                    f"{shortest:<22} {_source(session, job, sources):<15} {kids}"
                )


def _source(session: Session, job: Job, sources: dict[int, str]) -> str:
    """Where the search for this structure started (from the nearest selection record)."""
    while job is not None:
        if job.id in sources:
            return sources[job.id]
        job = session.get(Job, job.parent_id) if job.parent_id else None
    return "?"


def _campaign(session: Session, name: str) -> Campaign:
    campaign = session.exec(select(Campaign).where(Campaign.name == name)).first()
    if campaign is None:
        raise typer.BadParameter(f"no campaign named {name!r}")
    return campaign


def _raise_keyboard_interrupt(signum, frame) -> None:
    raise KeyboardInterrupt


def _print_status(session: Session, name: str) -> None:
    campaign = _campaign(session, name)
    stages = [s["name"] for s in campaign.spec["stages"]]
    selects = {s["name"] for s in campaign.spec["stages"] if s.get("select")}
    jobs = session.exec(select(Job).where(Job.campaign_id == campaign.id)).all()
    candidates = session.exec(select(Candidate).where(Candidate.campaign_id == campaign.id)).all()
    states = {row.id: row.to_state() for row in session.exec(select(StateRow)).all()}

    cells: dict[int, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for job in jobs:
        cells[job.state_id][job.stage][job.status] += 1
    for c in candidates:
        cells[c.state_id][c.stage]["seen"] += 1
        cells[c.state_id][c.stage]["selected"] += c.selected

    width = 10
    typer.echo(f"{'state':<11}" + "".join(f"{s:>{width}}" for s in stages))
    for state_id in sorted(cells, key=lambda i: states[i]):
        row = "".join(
            f"{_select_cell(cells[state_id][s]) if s in selects else _cell(cells[state_id][s]):>{width}}"
            for s in stages
        )
        typer.echo(f"{states[state_id].label:<11}{row}")

    totals = Counter(job.status for job in jobs)
    retried = sum(job.attempts > 1 for job in jobs)
    typer.echo(
        f"\n{len(jobs)} jobs: "
        + ", ".join(f"{totals[s]} {s}" for s in JobStatus)
        + f"; {retried} needed retries"
    )


def _select_cell(counter: Counter) -> str:
    return f"{counter['selected']}/{counter['seen']}" if counter["seen"] else "-"


def _cell(counter: Counter) -> str:
    """'✓' for one finished job, '✓3✗1' for several, '-' if the stage has no job yet."""
    if not counter:
        return "-"
    total = sum(counter.values())
    return "".join(
        SYMBOLS[s] + (str(counter[s]) if total > 1 else "") for s in JobStatus if counter[s]
    )
