import re
from datetime import datetime, timezone


def evidence_dict(row):
    return {k: getattr(row, k) for k in ["id", "quote", "start", "end", "section", "skills"]}


def valid_evidence(raw, row):
    # Evidence counts only if it is still an exact, non-empty substring of the CV text.
    return (
        0 <= row.start < row.end <= len(raw)
        and raw[row.start : row.end] == row.quote
        and bool(row.quote.strip())
    )


def date_intervals(text, current=None):
    """Find date ranges such as "Jan 2020 – Dec 2022" or "2021 - present".

    Returns (start, end) pairs counted in months.
    """
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
    """Total years covered by experience passages; overlapping jobs count once."""
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
    # Higher number = higher degree; 0 means no degree was recognised.
    if re.search(r"\b(ph\.?d|doctorate|doctoral)\b", text, re.I):
        return 8
    if re.search(r"\b(master|msc|m\.sc|mba)\b", text, re.I):
        return 7
    if re.search(r"\b(bachelor|bsc|b\.sc|b\.s)\b", text, re.I):
        return 6
    return 0


def match_requirement(req, evidence, raw):
    """Decide whether one job requirement is supported by a CV passage.

    A requirement is "met" only when a verified CV passage supports it.
    Everything else stays unverified; we never guess.
    """
    valid = [e for e in evidence if valid_evidence(raw, e)]
    found, tier = None, "unverified"
    if req.skill:
        # Skill requirements: a CV passage must mention the same vocabulary skill.
        found = next((e for e in valid if req.skill in e.skills), None)
        tier = "vocabulary"
        if found and req.min_years:
            # "3+ years of Python" needs dates on a passage that mentions Python,
            # not just enough total work experience.
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
        # General experience: one dated experience passage must cover the years.
        found = next(
            (e for e in valid if e.section == "experience" and years_of_experience([e]) >= req.min_years),
            None,
        )
        tier = "rules"
    elif req.category == "education":
        # Degrees: the CV must show the same level or higher (e.g. MSc satisfies BSc).
        needed = education_level(req.quote)
        found = next((e for e in valid if needed and education_level(e.quote) >= needed), None)
        tier = "rules"
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
    """Share of required (or preferred) requirements that are met, from 0 to 1."""
    rows = [r for r in decisions if r["required"] == required]
    return sum(r["status"] == "met" for r in rows) / len(rows) if rows else 0.0
