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
def extract(llm: bool = False):
    """Extract requirements for every eligible job (--llm uses the configured model)."""
    from .main import candidates, ensure_requirements
    from .schemas import Preferences

    with SessionLocal() as db:
        jobs = candidates(db, Preferences())
        for i, job in enumerate(jobs):
            ensure_requirements(db, job, llm)
            db.commit()
            if i % 25 == 0:
                typer.echo(f"Extracted {i + 1}/{len(jobs)}")
    typer.echo(f"Extracted {len(jobs)} jobs")
