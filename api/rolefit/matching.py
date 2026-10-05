import re
from datetime import datetime, timezone

from .skills import mentions


def needs_manual_review(text):
    # A matching keyword cannot prove depth, scale or responsibility.
    return bool(
        re.search(
            r"\b(?:advanced|expert|expertise|proficien\w*|fluent|fluency|extensive|strong|deep|"
            r"production|commercial|professional|at scale|leading|leadership|architect\w*)\b",
            text,
            re.I,
        )
    )


def evidence_dict(row):
    return {k: getattr(row, k) for k in ["id", "quote", "start", "end", "section", "skills"]}


def valid_evidence(raw, row):
    # Evidence counts only if it is still an exact, non-empty substring of the CV text.
    return (
        0 <= row.start < row.end <= len(raw)
        and raw[row.start : row.end] == row.quote
        and bool(row.quote.strip())
    )


DEGREES = (
    (1, r"\b(?:bachelor(?:'s)?|b\.?sc\.?|b\.?s\.?|beng)\b"),
    (2, r"\b(?:master(?:'s|s)?|m\.?sc\.?|m\.?s\.?|meng)\b"),
    (3, r"\b(?:ph\.?d\.?|doctorate|doctoral)\b"),
)
SUBJECTS = {
    "cs": r"\bcomputer science\b",
    "ai": r"\bartificial intelligence\b|\bAI\b",
    "software": r"\bsoftware engineering\b",
    "data": r"\bdata science\b",
}


def degree_level(text):
    levels = [level for level, pattern in DEGREES if re.search(pattern, text, re.I)]
    return min(levels) if levels else None


MONTHS = {
    name: i
    for i, name in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1
    )
}


def degree_end_date(text):
    """Return the end month of an education date range; year-only ends use December."""
    month = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
    match = re.search(
        rf"\b(?:{month}\s+)?(?:19|20)\d{{2}}\s*(?:[-–—]|to)\s*"
        rf"(?:(?P<month>{month})\s+)?(?P<year>(?:19|20)\d{{2}})\b",
        text,
        re.I,
    )
    if not match:
        return None
    end_month = MONTHS[match["month"][:3].lower()] if match["month"] else 12
    return int(match["year"]), end_month


def education_match(text, valid, raw):
    """Recognise a small set of related computing degrees; retain exact CV text."""
    required_level = degree_level(text)
    subjects = {key for key, pattern in SUBJECTS.items() if re.search(pattern, text, re.I)}
    if not required_level or not subjects:
        return None, "unverified", None
    related = bool(re.search(r"related (?:field|subject|discipline)", text, re.I))
    best = (None, "unverified", None)
    for row in valid:
        if row.section != "education" or not degree_level(row.quote):
            continue
        # Include nearby lines for a split subject/date, but stop before another degree.
        end = row.end
        following = sorted((e for e in valid if e.start >= row.end), key=lambda e: e.start)
        for next_row in following[:3]:
            if (
                next_row.section != "education"
                or degree_level(next_row.quote)
                or raw[end : next_row.start].strip()
            ):
                break
            end = next_row.end
        quote = raw[row.start : end]
        level = degree_level(row.quote)
        cv_subjects = {key for key, pattern in SUBJECTS.items() if re.search(pattern, quote, re.I)}
        if level < required_level or not (subjects & cv_subjects or (related and cv_subjects)):
            continue
        passage = {**evidence_dict(row), "quote": quote, "end": end}
        ongoing = re.search(
            r"\b(?:present|current|ongoing|expected|pursuing|in progress|not completed|incomplete|dropped out)\b",
            quote,
            re.I,
        )
        years = [int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", quote)]
        today = datetime.now(timezone.utc)
        current_month = (today.year, today.month)
        end_date = degree_end_date(quote)
        if ongoing or (end_date and end_date > current_month) or any(year > today.year for year in years):
            best = (passage, "education_in_progress", "Related degree in progress")
            continue
        completed = re.search(r"\b(?:graduated|completed|awarded|earned)\b", quote, re.I)
        dated = bool(end_date and end_date < current_month)
        # Additional constraints such as grades or accreditation need manual review.
        extra = re.search(r"gpa|grade|honou?rs|accredited|\band\b|years?", text, re.I)
        if (completed or dated) and not extra:
            return passage, "education", "Related degree found in your CV"
        best = (passage, "education_review", "Related degree found — check completion and requirements")
    return best


def match_requirement(req, evidence, raw):
    """Decide whether one job requirement is supported by a CV passage.

    A requirement is "met" only when a verified CV passage supports it.
    Everything else stays unverified; we never guess.
    """
    valid = [e for e in evidence if valid_evidence(raw, e)]
    if req.category == "education":
        passage, tier, note = education_match(req.text, valid, raw)
        return {
            "id": req.id,
            "text": req.text,
            "skill": req.skill,
            "required": req.required,
            "status": "met" if tier == "education" else "not_verified",
            "tier": tier,
            "evidence": passage,
            "note": note,
        }
    found, tier = None, "unverified"
    if req.skill:
        # Skill requirements: a CV passage must mention the same vocabulary skill.
        found = next(
            (
                e
                for e in sorted(valid, key=lambda e: e.section not in ("experience", "projects"))
                if req.skill in mentions(e.quote)
            ),
            None,
        )
        tier = "vocabulary"
        if (
            req.min_years
            or needs_manual_review(req.text)
            or (re.search(r"\bor\b", req.text, re.I) and len(mentions(req.text)) > 1)
        ):
            found = None
            tier = "manual_review"
    elif req.category == "experience":
        # Dates alone do not establish relevant work experience.
        tier = "manual_review"
    return {
        "id": req.id,
        "text": req.text,
        "skill": req.skill,
        "required": req.required,
        "status": "met" if found else "not_verified",
        "tier": tier if found else "unverified",
        "evidence": evidence_dict(found) if found else None,
    }


def coverage(decisions, required):
    """Share of required (or preferred) requirements that are met, from 0 to 1."""
    rows = [r for r in decisions if r["required"] == required]
    return sum(r["status"] == "met" for r in rows) / len(rows) if rows else 0.0


def requirement_score(decisions):
    """Weighted coverage of the groups present; no requirements means no score."""
    groups = [
        (required, weight)
        for required, weight in [(True, 0.85), (False, 0.15)]
        if any(r["required"] == required for r in decisions)
    ]
    if not groups:
        return None
    return int(
        100
        * sum(weight * coverage(decisions, required) for required, weight in groups)
        / sum(weight for _, weight in groups)
        + 0.5
    )
