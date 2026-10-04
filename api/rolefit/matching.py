def evidence_dict(row):
    return {k: getattr(row, k) for k in ["id", "quote", "start", "end", "section", "skills"]}


def valid_evidence(raw, row):
    # Evidence counts only if it is still an exact, non-empty substring of the CV text.
    return (
        0 <= row.start < row.end <= len(raw)
        and raw[row.start : row.end] == row.quote
        and bool(row.quote.strip())
    )


def match_requirement(req, evidence, raw):
    """Decide whether one job requirement is supported by a CV passage.

    A requirement is "met" only when a verified CV passage supports it.
    Everything else stays unverified; we never guess.
    """
    valid = [e for e in evidence if valid_evidence(raw, e)]
    found, tier = None, "unverified"
    if req.skill:
        # Skill requirements: a CV passage must mention the same vocabulary skill.
        found = next(
            (
                e
                for e in sorted(valid, key=lambda e: e.section not in ("experience", "projects"))
                if req.skill in e.skills
            ),
            None,
        )
        tier = "vocabulary"
        if req.min_years:
            found = None
            tier = "manual_review"
    elif req.category in ("experience", "education"):
        # Dates alone do not establish relevant experience, and a degree title alone
        # does not establish its completion, subject or alternatives. Keep these
        # constraints visible for manual review rather than claiming they are met.
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
