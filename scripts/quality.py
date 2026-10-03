"""Prepare blind audit samples and score reviewed JSON annotations."""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from rolefit.db import SessionLocal
from rolefit.models import Job
from rolefit.main import candidates, ensure_requirements
from rolefit.schemas import Preferences


def prepare():
    rng = random.Random(42)
    with SessionLocal() as db:
        jobs = list(db.scalars(select(Job)))

        def sample(rows, n):
            return rng.sample(rows, min(n, len(rows)))

        out = {
            "roles": [
                {"job_id": j.id, "title": j.title, "predicted": j.family, "gold": None}
                for j in sample(jobs, 100)
            ],
            "employment": [
                {"job_id": j.id, "title": j.title, "predicted": j.employment, "gold": None, "url": j.url}
                for j in sample([j for j in jobs if j.employment_provenance == "inferred"], 50)
            ],
            "closed": [
                {"job_id": j.id, "url": j.url, "predicted_open": j.is_open, "gold_open": None}
                for j in sample(jobs, 20)
            ],
        }
        groups = defaultdict(list)
        for job in candidates(db, Preferences()):
            groups[job.family].append(job)
        chosen = []
        for family, rows in sorted(groups.items()):
            chosen += sample(rows, 10)
        remaining = [j for rows in groups.values() for j in rows if j not in chosen]
        chosen += sample(remaining, max(0, 50 - len(chosen)))
        out["requirements"] = [
            {
                "job_id": j.id,
                "family": j.family,
                "url": j.url,
                "predicted": [
                    {"skill": r.skill, "category": r.category, "required": r.required}
                    for r in ensure_requirements(db, j)
                ],
                "gold": None,
            }
            for j in chosen
        ]
        db.commit()
    Path("data/quality/audit.json").write_text(json.dumps(out, indent=2))
    print("Review data/quality/audit.json. Null gold fields are deliberately ungraded.")


def score(path):
    data = json.loads(path.read_text())
    out = {}
    for key, field, pred in [
        ("roles", "gold", "predicted"),
        ("employment", "gold", "predicted"),
        ("closed", "gold_open", "predicted_open"),
    ]:
        rows = [r for r in data[key] if r[field] is not None]
        out[key] = {
            "reviewed": len(rows),
            "accuracy": sum(r[field] == r[pred] for r in rows) / len(rows) if rows else None,
        }
    families = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    for row in data["requirements"]:
        if row["gold"] is None:
            continue
        pred = {(r["skill"], r["category"]): r["required"] for r in row["predicted"]}
        gold = {(r["skill"], r["category"]): r["required"] for r in row["gold"]}
        common = pred.keys() & gold.keys()
        v = families[row["family"]]
        v[0] += len(common)
        v[1] += len(pred)
        v[2] += len(gold)
        v[3] += sum(pred[k] == gold[k] for k in common)
        v[4] += len(common)
        v[5] += 1

    def summarize(values):
        tp, npred, ngold, correct, nflags, n = values
        return {
            "f1": 2 * tp / (npred + ngold) if npred + ngold else 0.0,
            "required_preferred_accuracy": correct / nflags if nflags else None,
            "postings": n,
        }

    out["per_family"] = {k: summarize(v) for k, v in families.items()}
    out["extraction"] = summarize([sum(v[i] for v in families.values()) for i in range(6)])
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "score"])
    parser.add_argument("--input", type=Path, default=Path("data/quality/audit.json"))
    args = parser.parse_args()
    prepare() if args.command == "prepare" else score(args.input)
