import asyncio
import json
from pathlib import Path

import typer
from sqlalchemy import select

from .config import ROOT
from .db import SessionLocal
from .models import CV, Evidence, Requirement

app = typer.Typer(help="RoleFit ingestion, extraction and evaluation workflow")


@app.command()
def crawl(seeds: Path = ROOT / "data/seeds.json"):
    """Crawl all configured boards, with safe idempotent reconciliation."""
    from .ingestion import crawl as run

    with SessionLocal() as db:
        report = asyncio.run(run(db, seeds))
    (ROOT / "work/yield.json").write_text(json.dumps(report, indent=2))
    typer.echo(json.dumps(report, indent=2))


@app.command()
def extract(llm: bool = False):
    """Extract candidate requirements; --llm enables configured validated model."""
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


@app.command()
def embed():
    """Compute true 768-d bge chunk embeddings; requires pip install -e '.[ml]'."""
    from rolefit_ml.embeddings import embedder
    from .main import candidates
    from .schemas import Preferences

    model = embedder()
    with SessionLocal() as db:
        for job in candidates(db, Preferences()):
            if job.embedding is None:
                job.embedding = model.document(job.title + "\n" + job.description)
        for cls in [Evidence, Requirement]:
            for row in db.scalars(select(cls)):
                if row.embedding is None:
                    row.embedding = model.document(row.quote)
        db.commit()
    typer.echo("Embeddings stored; every input chunk checked <=512 tokens")


@app.command()
def freeze(output: Path = ROOT / "data/evaluation/snapshot.json", demo: bool = False):
    """Freeze structured jobs and features only; never publish full job descriptions."""
    from rolefit_ml.dataset import freeze_snapshot

    with SessionLocal() as db:
        snapshot = freeze_snapshot(db, demo=demo)
    output.write_text(json.dumps(snapshot, indent=2))
    typer.echo(f"Frozen {len(snapshot['jobs'])} jobs to {output}")


@app.command()
def evaluate(
    snapshot: Path = ROOT / "data/evaluation/snapshot.json",
    labels: Path = ROOT / "data/evaluation/labels.json",
    output: Path = ROOT / "data/evaluation/results.json",
):
    """Regenerate real LOPO metrics, ablations and learning curve; refuse missing data."""
    from rolefit_ml.evaluation import run

    report = run(json.loads(snapshot.read_text()), json.loads(labels.read_text()))
    output.write_text(json.dumps(report, indent=2))
    typer.echo(report["conclusion"])


@app.command()
def load_persona(path: Path):
    """Load a public persona fixture into its own deterministic user (no real contacts)."""
    import hashlib
    import uuid
    from .extraction import extract_cv
    from .models import User

    fixture = json.loads(path.read_text())
    user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "rolefit:" + fixture["id"]))
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user:
            db.add(User(id=user_id, preferences=fixture["preferences"]))
            db.flush()
        raw = fixture["text"]
        items, failures, total = extract_cv(raw)
        cv = CV(
            user_id=user_id,
            text=raw,
            filename=fixture["id"] + ".txt",
            content_hash=hashlib.sha256(raw.encode()).hexdigest(),
            model_version="deterministic-preview-v1",
            prompt_version="evidence-v1",
            verification_failures=failures,
            extraction_count=total,
        )
        db.add(cv)
        db.flush()
        db.add_all([Evidence(cv_id=cv.id, **item) for item in items])
        db.commit()
    typer.echo(user_id)


@app.command()
def train_winner():
    """Export the winning method only after a completed human evaluation."""
    from rolefit_ml.winner import export

    snapshot = json.loads((ROOT / "data/evaluation/snapshot.json").read_text())
    labels = json.loads((ROOT / "data/evaluation/labels.json").read_text())
    report = json.loads((ROOT / "data/evaluation/results.json").read_text())
    artifact = export(snapshot, labels, report)
    typer.echo("Exported winning method: " + artifact["method"])
