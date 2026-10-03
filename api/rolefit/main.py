import hashlib
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from rolefit_ml.retrieval import BM25

from .auth import current_user
from .config import settings
from .db import get_db
from .extraction import PROMPT_VERSION, extract_cv, extract_requirements, parse_file
from .matching import coverage, evidence_dict, features
from .models import CV, CrawlRun, Decision, Evidence, ExtractionCache, Job, Requirement, User
from .schemas import DecisionInput, Preferences

app = FastAPI(
    title="RoleFit",
    version="0.1.0",
    description="Evidence-grounded matching. Preview scores are not hiring probabilities.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def latest_cv(db, user):
    return db.scalar(select(CV).where(CV.user_id == user.id).order_by(CV.created_at.desc()))


def candidates(db, prefs):
    query = select(Job).where(
        Job.is_open.is_(True),
        Job.duplicate_of.is_(None),
        Job.language == "en",
        Job.family.is_not(None),
        Job.employment.in_(prefs.employment),
    )
    if prefs.families:
        query = query.where(Job.family.in_(prefs.families))
    jobs = list(db.scalars(query))
    # Country is a hard filter. Unknown countries never match an explicit selection.
    if prefs.countries:
        jobs = [j for j in jobs if set(j.countries) & set(prefs.countries)]
    return jobs


def ensure_requirements(db, job, use_llm=False):
    reqs = list(db.scalars(select(Requirement).where(Requirement.job_id == job.id)))
    if reqs and (
        not use_llm
        or all(r.model_version == settings().llm_model and r.prompt_version == PROMPT_VERSION for r in reqs)
    ):
        return reqs
    # Upgrade deterministic preview extractions explicitly when --llm is requested.
    if reqs:
        db.execute(delete(Requirement).where(Requirement.job_id == job.id))
        reqs = []
    for item in extract_requirements(job.description, db, use_llm):
        row = Requirement(
            job_id=job.id,
            **item,
            model_version=settings().llm_model if use_llm else "deterministic-preview-v1",
            prompt_version=PROMPT_VERSION,
        )
        db.add(row)
        reqs.append(row)
    db.flush()
    return reqs


def job_payload(db, job, cv, evidence, bm25_score=0):
    requirements = ensure_requirements(db, job)
    vector, decisions = features(job, requirements, evidence, cv.text, bm25_score)
    score = round(100 * (0.85 * coverage(decisions, True) + 0.15 * coverage(decisions, False)))
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "countries": job.countries,
        "family": job.family,
        "employment": job.employment,
        "employment_provenance": job.employment_provenance,
        "workplace": job.workplace,
        "provider": job.provider,
        "url": job.url,
        "score": score,
        "required_coverage": coverage(decisions, True),
        "requirements": decisions,
        "first_seen": job.first_seen.isoformat(),
        "method": "Evidence coverage preview (untrained)",
        "features": vector,
    }


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "environment": settings().app_env,
        "authentication": "development only" if settings().dev_auth else "Supabase JWT",
    }


@app.get("/auth/callback")
def auth_callback(user: User = Depends(current_user)):
    return {"user_id": user.id}


@app.get("/me")
def me(db: Session = Depends(get_db), user: User = Depends(current_user)):
    cv = latest_cv(db, user)
    evidence = list(db.scalars(select(Evidence).where(Evidence.cv_id == cv.id))) if cv else []
    decisions = list(db.scalars(select(Decision).where(Decision.user_id == user.id)))
    return {
        "cv": {
            "id": cv.id,
            "filename": cv.filename,
            "verification_failures": cv.verification_failures,
            "extraction_count": cv.extraction_count,
            "model_version": cv.model_version,
        }
        if cv
        else None,
        "evidence": [evidence_dict(e) for e in evidence],
        "preferences": user.preferences,
        "saved": [d.job_id for d in decisions if d.state == "saved"],
        "skipped": [d.job_id for d in decisions if d.state == "skipped"],
    }


@app.post("/cv")
async def upload_cv(
    file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)
):
    try:
        data = await file.read(5 * 1024 * 1024 + 1)
        filename = Path(file.filename or "cv.txt").name[:200]
        raw = parse_file(data, filename)
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, str(exc)) from None
    except Exception:
        raise HTTPException(
            422, "Could not read this document. Try exporting it as a text-based PDF or TXT."
        ) from None
    finally:
        await file.close()  # Close and remove Starlette's temporary original, even on failure.
    del data
    use_llm = bool(settings().llm_api_key and settings().llm_model)
    try:
        items, failed, total = extract_cv(raw, db, user.id, use_llm)
    except Exception as exc:
        # Do not expose upstream payloads or provider credentials.
        raise HTTPException(422, "CV structuring failed. Check extraction configuration and budget.") from exc
    if not items:
        raise HTTPException(422, "No verifiable evidence was found")
    db.execute(delete(CV).where(CV.user_id == user.id))
    cv = CV(
        user_id=user.id,
        text=raw,
        content_hash=hashlib.sha256(raw.encode()).hexdigest(),
        filename=filename,
        model_version=settings().llm_model if use_llm else "deterministic-preview-v1",
        prompt_version=PROMPT_VERSION,
        verification_failures=failed,
        extraction_count=total,
    )
    db.add(cv)
    db.flush()
    evidence = [Evidence(cv_id=cv.id, **item) for item in items]
    db.add_all(evidence)
    db.commit()
    return {
        "id": cv.id,
        "filename": filename,
        "evidence": [evidence_dict(e) for e in evidence],
        "verification_failures": failed,
        "extraction_count": total,
        "failure_rate": failed / total if total else 0,
        "model_version": cv.model_version,
    }


@app.delete("/cv", status_code=204)
def delete_cv(db: Session = Depends(get_db), user: User = Depends(current_user)):
    cv_ids = list(db.scalars(select(CV.id).where(CV.user_id == user.id)))
    db.execute(
        delete(ExtractionCache).where(
            ExtractionCache.scope.in_([user.id] + ["adjudication:" + c for c in cv_ids])
        )
    )
    db.execute(delete(CV).where(CV.user_id == user.id))
    db.commit()


@app.delete("/me", status_code=204)
def delete_user_data(db: Session = Depends(get_db), user: User = Depends(current_user)):
    delete_cv(db, user)
    db.delete(user)
    db.commit()


@app.put("/preferences")
def preferences(value: Preferences, db: Session = Depends(get_db), user: User = Depends(current_user)):
    user.preferences = value.model_dump()
    db.commit()
    return user.preferences


@app.post("/matches")
def matches(db: Session = Depends(get_db), user: User = Depends(current_user)):
    cv = latest_cv(db, user)
    if cv is None:
        raise HTTPException(409, "Add a CV before finding matches")
    prefs = Preferences.model_validate(user.preferences)
    jobs = candidates(db, prefs)
    evidence = list(db.scalars(select(Evidence).where(Evidence.cv_id == cv.id)))
    lexical = BM25([j.title + "\n" + j.description for j in jobs]).score(cv.text)
    result = [job_payload(db, j, cv, evidence, float(score)) for j, score in zip(jobs, lexical)]
    from rolefit_ml.winner import ARTIFACT, score as learned_score

    if ARTIFACT.exists():
        import json
        from rolefit_ml.retrieval import retrieve

        artifact = json.loads(ARTIFACT.read_text())
        method = artifact["method"]
        if method in ("dense", "hybrid", "feature"):
            from rolefit_ml.embeddings import embedder

            model = embedder()
            for ev in evidence:
                if ev.embedding is None:
                    ev.embedding = model.document(ev.quote)
            for job in jobs:
                if job.embedding is None:
                    job.embedding = model.document(job.title + "\n" + job.description)
                for req in ensure_requirements(db, job):
                    if req.embedding is None:
                        req.embedding = model.document(req.quote)
            result = [job_payload(db, j, cv, evidence, float(s)) for j, s in zip(jobs, lexical)]
        if result:
            if method == "feature":
                ranking = dict(
                    zip([r["id"] for r in result], learned_score(artifact, [r["features"] for r in result]))
                )
            else:
                ranking = dict(
                    retrieve(
                        method, jobs, cv.text, [e.embedding for e in evidence if e.embedding is not None]
                    )
                )
            for row in result:
                row["rank_score"] = float(ranking[row["id"]])
                row["method"] = f"Ranked by evaluated {method}; displayed score is evidence coverage"
            result.sort(key=lambda j: (-j["rank_score"], j["id"]))
    else:
        result.sort(key=lambda j: (-j["score"], -j["features"][0], j["id"]))
    for row in result:
        row.pop("features")
    db.commit()
    return {
        "jobs": result,
        "candidate_count": len(jobs),
        "method": "Evidence coverage preview; evaluation pending",
    }


@app.get("/jobs/{job_id}")
def job_detail(job_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    job, cv = db.get(Job, job_id), latest_cv(db, user)
    if not job:
        raise HTTPException(404, "Job not found")
    if not cv:
        raise HTTPException(409, "Add a CV first")
    evidence = list(db.scalars(select(Evidence).where(Evidence.cv_id == cv.id)))
    result = job_payload(db, job, cv, evidence)
    result["description"] = job.description
    result["is_open"] = job.is_open
    result.pop("features")
    db.commit()
    return result


@app.put("/jobs/{job_id}/decision")
def decision(
    job_id: str, value: DecisionInput, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    if not db.get(Job, job_id):
        raise HTTPException(404, "Job not found")
    row = db.scalar(select(Decision).where(Decision.user_id == user.id, Decision.job_id == job_id))
    if value.state == "none":
        if row:
            db.delete(row)
    elif row:
        row.state = value.state
    else:
        db.add(Decision(user_id=user.id, job_id=job_id, state=value.state))
    db.commit()
    return {"state": value.state}


@app.get("/corpus/status")
def corpus_status(db: Session = Depends(get_db), user: User = Depends(current_user)):
    run = db.scalar(select(CrawlRun).order_by(CrawlRun.started_at.desc()))
    return run.report if run else {"eligible": 0, "corpus_gate_passed": False}
