import hashlib
import json
import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from rolefit.config import ROOT
from rolefit.main import candidates, ensure_requirements
from rolefit.matching import features
from rolefit.models import CV, Evidence, User
from rolefit.schemas import Preferences
from rolefit.skills import vocabulary
from .retrieval import retrieve


def freeze_snapshot(db, demo=False):
    personas = [json.loads(p.read_text()) for p in sorted((ROOT / "data/personas").glob("*.json"))]
    if len(personas) != 8 or (not demo and any(p.get("origin") != "human-authored" for p in personas)):
        raise ValueError(
            "Replace all eight draft personas with human-authored anonymised CV fixtures before freezing"
        )
    if not demo and vocabulary().get("status") != "frozen-esco":
        raise ValueError("Import, review and freeze the ESCO vocabulary before evaluation")
    timestamp = datetime.now(timezone.utc)
    jobs_out, pairs = {}, []
    for persona in personas:
        user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "rolefit:" + persona["id"]))
        user = db.get(User, user_id)
        if not user:
            raise ValueError(f"Load persona {persona['id']} first")
        cv = db.scalar(select(CV).where(CV.user_id == user_id).order_by(CV.created_at.desc()))
        evidence = list(db.scalars(select(Evidence).where(Evidence.cv_id == cv.id)))
        jobs = candidates(db, Preferences.model_validate(persona["preferences"]))
        if len(jobs) < 100:
            raise ValueError(f"Broaden preferences for {persona['id']}; fewer than 100 eligible jobs")
        rankings = {
            method: dict(
                retrieve(method, jobs, cv.text, [e.embedding for e in evidence if e.embedding is not None])
            )
            for method in ["bm25", "dense", "hybrid"]
        }
        for job in jobs:
            reqs = ensure_requirements(db, job)
            if any(r.embedding is None for r in reqs) or any(e.embedding is None for e in evidence):
                raise ValueError("Every requirement and evidence row must have an embedding before freezing")
            vec, _ = features(job, reqs, evidence, cv.text, rankings["bm25"][job.id], timestamp)
            pairs.append(
                {
                    "persona_id": persona["id"],
                    "job_id": job.id,
                    "features": vec,
                    **{m: r[job.id] for m, r in rankings.items()},
                }
            )
            jobs_out[job.id] = {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "url": job.url,
                "provider": job.provider,
                "board": job.board,
                "external_id": job.external_id,
                "content_hash": job.content_hash,
                "employment_provenance": job.employment_provenance,
                "requirements": [
                    {
                        "id": r.id,
                        "category": r.category,
                        "skill": r.skill,
                        "required": r.required,
                        "min_years": r.min_years,
                        "model_version": r.model_version,
                        "prompt_version": r.prompt_version,
                    }
                    for r in reqs
                ],
            }
    if len(jobs_out) < 200:
        raise ValueError("Frozen corpus must contain at least 200 unique relevant postings")
    payload = {
        "status": "synthetic-demo" if demo else "human-evaluation",
        "frozen_at": timestamp.isoformat(),
        "vocabulary_status": vocabulary()["status"],
        "vocabulary_hash": hashlib.sha256((ROOT / "data/skills.json").read_bytes()).hexdigest(),
        "jobs": list(jobs_out.values()),
        "personas": personas,
        "pairs": pairs,
    }
    payload["content_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return payload


def pool(snapshot):
    out = []
    for persona in snapshot["personas"]:
        rows = [r for r in snapshot["pairs"] if r["persona_id"] == persona["id"]]
        selected = set()
        for method in ["bm25", "dense", "hybrid"]:
            selected.update(r["job_id"] for r in sorted(rows, key=lambda r: (-r[method], r["job_id"]))[:10])
        remaining = sorted(r["job_id"] for r in rows if r["job_id"] not in selected)
        # Aim for 35 judgements/persona; include at least five random in-family controls.
        selected.update(random.Random(42).sample(remaining, min(len(remaining), max(5, 35 - len(selected)))))
        out.extend({"persona_id": persona["id"], "job_id": j} for j in sorted(selected))
    return out
