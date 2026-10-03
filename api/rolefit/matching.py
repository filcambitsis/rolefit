import re
from datetime import datetime, timezone

import numpy as np

from .extraction import verified_span

FEATURE_NAMES = [
    "bm25",
    "document_cosine",
    "max_chunk_cosine",
    "mean_chunk_cosine",
    "required_coverage",
    "preferred_coverage",
    "critical_missing",
    "years_gap",
    "seniority_gap",
    "education_satisfied",
    "language_satisfied",
    "freshness",
]


def evidence_dict(row):
    return {k: getattr(row, k) for k in ["id", "quote", "start", "end", "section", "skills"]}


def valid_evidence(raw, row):
    return (
        0 <= row.start < row.end <= len(raw)
        and raw[row.start : row.end] == row.quote
        and bool(row.quote.strip())
    )


def date_intervals(text, current=None):
    current = current or datetime.now(timezone.utc)
    pattern = r"(?:(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+)?((?:19|20)\d{2})\s*[-–—]\s*(?:(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+)?((?:19|20)\d{2}|present|current)"
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    intervals = []
    for m1, y1, m2, y2 in re.findall(pattern, text, re.I):
        start = int(y1) * 12 + (
            months.index(m1[:3].lower()) if m1 else 11
        )  # Conservative for year-only ranges.
        end = (
            current.year * 12 + current.month - 1
            if y2.lower() in ("present", "current")
            else int(y2) * 12 + (months.index(m2[:3].lower()) + 1 if m2 else 0)
        )
        if end > start:
            intervals.append((start, end))
    return intervals


def years_of_experience(evidence, current=None):
    intervals = sorted(
        interval
        for e in evidence
        if e.section == "experience"
        for interval in date_intervals(e.quote, current)
    )
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return sum(end - start for start, end in merged) / 12


def education_level(text):
    if re.search(r"\b(ph\.?d|doctorate|doctoral)\b", text, re.I):
        return 8
    if re.search(r"\b(master|msc|m\.sc|mba)\b", text, re.I):
        return 7
    if re.search(r"\b(bachelor|bsc|b\.sc|b\.s)\b", text, re.I):
        return 6
    return 0


def seniority(text):
    if re.search(r"\b(principal|staff|lead|head|director)\b", text, re.I):
        return 3
    if re.search(r"\b(senior|sr)\b", text, re.I):
        return 2
    if re.search(r"\b(junior|intern|graduate|entry)\b", text, re.I):
        return 0
    return 1


def match_requirement(req, evidence, raw, db=None, adjudicate=False):
    # Verify ownership upstream and exact offsets again here: there is no unchecked met path.
    valid = [e for e in evidence if valid_evidence(raw, e)]
    found, tier = None, "unverified"
    if req.skill:
        found = next((e for e in valid if req.skill in e.skills), None)
        tier = "vocabulary"
        if found and req.min_years:
            # Skill years must be attached to that skill; generic total experience is insufficient.
            found = next(
                (
                    e
                    for e in valid
                    if req.skill in e.skills
                    and sum((b - a) / 12 for a, b in date_intervals(e.quote)) >= req.min_years
                ),
                None,
            )
            tier = "rules"
    elif req.category == "experience" and req.min_years is not None:
        found = next(
            (e for e in valid if e.section == "experience" and years_of_experience([e]) >= req.min_years),
            None,
        )
        tier = "rules"
    elif req.category == "education":
        needed = education_level(req.quote)
        found = next((e for e in valid if needed and education_level(e.quote) >= needed), None)
        tier = "rules"
    if found is None and adjudicate and req.category in ("other", "skill"):
        from .extraction import Adjudication, cached_call
        import json

        prompt = json.dumps({"requirement": req.quote, "evidence": [e.quote for e in valid]})
        result = cached_call(
            db,
            "adjudication:" + evidence[0].cv_id if evidence else "empty",
            "adjudication",
            prompt,
            Adjudication,
            "Does one CV passage substantiate this requirement? Use met=false when uncertain. If met, evidence_quote must be one exact complete passage supplied. Never judge years or education numerically.",
        )
        if result.met and result.evidence_quote and verified_span(raw, result.evidence_quote):
            found = next((e for e in valid if e.quote == result.evidence_quote), None)
            tier = "adjudication"
    return {
        "id": req.id,
        "text": req.text,
        "skill": req.skill,
        "required": req.required,
        "status": "met" if found else "missing",
        "tier": tier if found else "unverified",
        "evidence": evidence_dict(found) if found else None,
    }


def coverage(decisions, required):
    rows = [r for r in decisions if r["required"] == required]
    return sum(r["status"] == "met" for r in rows) / len(rows) if rows else 0.0


def features(job, requirements, evidence, cv_text, bm25_score=0.0, reference_date=None):
    reference_date = reference_date or datetime.now(timezone.utc)
    decisions = [match_requirement(r, evidence, cv_text) for r in requirements]
    ev_vectors = np.array([e.embedding for e in evidence if e.embedding is not None])
    req_vectors = np.array([r.embedding for r in requirements if r.embedding is not None])
    doc_cos, maximum, mean = 0.0, 0.0, 0.0
    if ev_vectors.size and req_vectors.size:
        sims = ev_vectors @ req_vectors.T
        maximum, mean = float(sims.max()), float(sims.max(axis=0).mean())
        if job.embedding is not None:
            pooled = ev_vectors.mean(axis=0)
            pooled /= max(float(np.linalg.norm(pooled)), 1e-9)
            doc_cos = float(pooled @ np.asarray(job.embedding))
    years_required = max((r.min_years or 0 for r in requirements), default=0)
    valid = [e for e in evidence if valid_evidence(cv_text, e)]
    edu = [d for d, r in zip(decisions, requirements) if r.category == "education"]
    lang = [d for d, r in zip(decisions, requirements) if r.category == "language"]
    first_seen = job.first_seen.replace(tzinfo=timezone.utc)
    vector = [
        bm25_score,
        doc_cos,
        maximum,
        mean,
        coverage(decisions, True),
        coverage(decisions, False),
        sum(d["required"] and d["status"] == "missing" for d in decisions),
        max(0.0, years_required - years_of_experience(valid, reference_date)),
        max(0.0, seniority(job.title) - seniority(cv_text)),
        float(all(d["status"] == "met" for d in edu)),
        float(all(d["status"] == "met" for d in lang)),
        float(np.exp(-max(0, (reference_date - first_seen).days) / 90)),
    ]
    return vector, decisions
