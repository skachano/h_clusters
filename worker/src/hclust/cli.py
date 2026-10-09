"""Command line: python -m hclust plan|run|status."""

import signal
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Annotated

import typer
from sqlmodel import Session, select

from hclust.campaign import CampaignSpec
from hclust.db import Campaign, Job, JobStatus, StateRow, get_engine
from hclust.runner import Runner, plan as plan_campaign

app = typer.Typer(no_args_is_help=True, add_completion=False)

SYMBOLS = {
    JobStatus.DONE: "✓",
    JobStatus.FAILED: "✗",
    JobStatus.RUNNING: "▶",
    JobStatus.PENDING: "·",
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


@app.command()
def status(name: Annotated[str, typer.Argument(help="campaign name or YAML file")]) -> None:
    """Show a states × stages table of job statuses."""
    if name.endswith((".yaml", ".yml")):
        name = CampaignSpec.load(Path(name)).name
    with Session(get_engine()) as session:
        _print_status(session, name)


def _raise_keyboard_interrupt(signum, frame) -> None:
    raise KeyboardInterrupt


def _print_status(session: Session, name: str) -> None:
    campaign = session.exec(select(Campaign).where(Campaign.name == name)).first()
    if campaign is None:
        raise typer.BadParameter(f"no campaign named {name!r}")
    stages = [s["name"] for s in campaign.spec["stages"]]
    jobs = session.exec(select(Job).where(Job.campaign_id == campaign.id)).all()
    states = {row.id: row.to_state() for row in session.exec(select(StateRow)).all()}

    cells: dict[int, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for job in jobs:
        cells[job.state_id][job.stage][job.status] += 1

    width = 9
    typer.echo(f"{'state':<11}" + "".join(f"{s:>{width}}" for s in stages))
    for state_id in sorted(cells, key=lambda i: states[i]):
        row = "".join(f"{_cell(cells[state_id][s]):>{width}}" for s in stages)
        typer.echo(f"{states[state_id].label:<11}{row}")

    totals = Counter(job.status for job in jobs)
    retried = sum(job.attempts > 1 for job in jobs)
    typer.echo(
        f"\n{len(jobs)} jobs: "
        + ", ".join(f"{totals[s]} {s}" for s in JobStatus)
        + f"; {retried} needed retries"
    )


def _cell(counter: Counter) -> str:
    """'✓' for one finished job, '✓3✗1' for several, '-' if the stage has no job yet."""
    if not counter:
        return "-"
    total = sum(counter.values())
    return "".join(
        SYMBOLS[s] + (str(counter[s]) if total > 1 else "") for s in JobStatus if counter[s]
    )
