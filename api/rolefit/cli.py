import asyncio
import json
from pathlib import Path

import typer

from .config import ROOT
from .db import SessionLocal

app = typer.Typer(help="RoleFit job collection and requirement extraction")


@app.command()
def crawl(seeds: Path = ROOT / "data/seeds.json"):
    """Fetch job postings from every board in the seeds file and update the database."""
    from .ingestion import crawl as run

    with SessionLocal() as db:
        report = asyncio.run(run(db, seeds))
    (ROOT / "work/yield.json").write_text(json.dumps(report, indent=2))
    typer.echo(json.dumps(report, indent=2))


@app.command()
def extract():
    """Extract requirements for every eligible job."""
    from .main import candidates, ensure_requirements
    from .schemas import Preferences

    with SessionLocal() as db:
        jobs = candidates(db, Preferences())
        for i, job in enumerate(jobs):
            ensure_requirements(db, job)
            db.commit()
            if i % 25 == 0:
                typer.echo(f"Extracted {i + 1}/{len(jobs)}")
    typer.echo(f"Extracted {len(jobs)} jobs")


@app.command()
def refresh(seeds: Path = ROOT / "data/seeds.json"):
    """Refresh public jobs, extract requirements and report any failed sources."""
    from .ingestion import crawl as run
    from .main import candidates, ensure_requirements
    from .schemas import Preferences

    with SessionLocal() as db:
        report = asyncio.run(run(db, seeds))
        jobs = candidates(db, Preferences())
        no_requirements = 0
        for job in jobs:
            if not ensure_requirements(db, job):
                no_requirements += 1
            db.commit()
        report["extracted_jobs"] = len(jobs)
        report["without_requirements"] = no_requirements
        report["failed_boards"] = sum("error" in board for board in report["boards"])
    (ROOT / "work").mkdir(exist_ok=True)
    (ROOT / "work/yield.json").write_text(json.dumps(report, indent=2))
    typer.echo(json.dumps(report, indent=2))
    if report["failed_boards"]:
        typer.echo("Some boards failed; their existing jobs were preserved.", err=True)
        raise typer.Exit(1)
