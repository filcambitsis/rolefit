import hashlib
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from .auth import current_user
from .config import settings
from .db import get_db
from .extraction import PROMPT_VERSION, extract_cv, extract_requirements, parse_file
from .matching import coverage, evidence_dict, match_requirement, requirement_score
from .models import CV, CrawlRun, Decision, Evidence, ExtractionCache, Job, Requirement, User
from .normalization import FAMILIES
from .ranking import bm25_scores
from .schemas import DecisionInput, Preferences
from .skills import mentions

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


def cv_evidence(db, cv):
    rows = list(db.scalars(select(Evidence).where(Evidence.cv_id == cv.id)))
    # Rebuild older local extractions to recover short skills and revised headings.
    # Never resend an existing CV to an external model during a read.
    if cv.prompt_version != PROMPT_VERSION and cv.model_version == "deterministic-preview-v1":
        items, failed, total = extract_cv(cv.text)
        db.execute(delete(Evidence).where(Evidence.cv_id == cv.id))
        rows = [Evidence(cv_id=cv.id, **item) for item in items]
        db.add_all(rows)
        cv.prompt_version = PROMPT_VERSION
        cv.verification_failures, cv.extraction_count = failed, total
        db.flush()
    # Model-extracted passages keep their quotes and provenance; only skill tags change.
    for row in rows:
        skills = mentions(row.quote)
        if row.skills != skills:
            row.skills = skills
    return rows


def clear_cv_cache(db, user):
    cv_ids = db.scalars(select(CV.id).where(CV.user_id == user.id))
    scopes = [user.id, *("adjudication:" + cv_id for cv_id in cv_ids)]
    # Old adjudication results can contain CV quotes even though the feature is gone.
    db.execute(delete(ExtractionCache).where(ExtractionCache.scope.in_(scopes)))


def saved_preferences(user):
    # Ignore role families that no longer exist, so old saved preferences still load.
    prefs = dict(user.preferences or {})
    prefs["families"] = [f for f in prefs.get("families", []) if f in FAMILIES]
    return Preferences.model_validate(prefs)


def candidates(db, prefs):
    """Open, English, de-duplicated jobs that pass the user's hard filters."""
    query = select(Job).where(
        Job.is_open.is_(True),
        Job.duplicate_of.is_(None),
        Job.language == "en",
        Job.family.in_(FAMILIES),
        Job.employment.in_(prefs.employment),
    )
    if prefs.families:
        query = query.where(Job.family.in_(prefs.families))
    jobs = list(db.scalars(query))
    # Netherlands-only, including remote roles explicitly available here.
    return [job for job in jobs if "NL" in job.countries]


def ensure_requirements(db, job, use_llm=False):
    """Return a job's requirements, extracting them again if missing or outdated."""
    reqs = list(db.scalars(select(Requirement).where(Requirement.job_id == job.id)))
    up_to_date = all(r.prompt_version == PROMPT_VERSION for r in reqs) and (
        not use_llm or all(r.model_version == settings().llm_model for r in reqs)
    )
    if reqs and up_to_date:
        return reqs
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


def job_payload(db, job, cv, evidence):
    """A job plus, for each requirement, whether the CV supports it."""
    requirements = ensure_requirements(db, job)
    decisions = [match_requirement(r, evidence, cv.text) for r in requirements]
    score = requirement_score(decisions)
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
        "method": "Requirement coverage",
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
    evidence = cv_evidence(db, cv) if cv else []
    db.commit()
    decisions = [
        decision
        for decision, job in db.execute(
            select(Decision, Job).join(Job, Decision.job_id == Job.id).where(Decision.user_id == user.id)
        )
        if "NL" in job.countries
    ]
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
        "preferences": saved_preferences(user).model_dump(),
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
    clear_cv_cache(db, user)
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
    # Also remove any cached model output made from this user's CV.
    clear_cv_cache(db, user)
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
    jobs = candidates(db, saved_preferences(user))
    evidence = cv_evidence(db, cv)
    result = [job_payload(db, job, cv, evidence) for job in jobs]
    # Rank by requirement coverage. When two jobs tie, the one whose text
    # shares more words with the CV (BM25) comes first.
    overlap = bm25_scores([j.title + "\n" + j.description for j in jobs], cv.text)
    ranked = sorted(
        zip(result, overlap),
        key=lambda pair: (
            -(pair[0]["score"] if pair[0]["score"] is not None else -1),
            -pair[1],
            pair[0]["id"],
        ),
    )
    db.commit()
    return {
        "jobs": [row for row, _ in ranked],
        "candidate_count": len(jobs),
        "method": "Requirement coverage",
    }


@app.get("/jobs/{job_id}")
def job_detail(job_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    job, cv = db.get(Job, job_id), latest_cv(db, user)
    if not job or "NL" not in job.countries:
        raise HTTPException(404, "Job not found")
    if not cv:
        raise HTTPException(409, "Add a CV first")
    evidence = cv_evidence(db, cv)
    result = job_payload(db, job, cv, evidence)
    result["description"] = job.description
    result["is_open"] = job.is_open
    db.commit()
    return result


@app.put("/jobs/{job_id}/decision")
def decision(
    job_id: str, value: DecisionInput, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    job = db.get(Job, job_id)
    if not job or ("NL" not in job.countries and value.state != "none"):
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
    return run.report if run else {"eligible": 0}
