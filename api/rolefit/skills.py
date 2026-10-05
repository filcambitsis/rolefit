import json
import re
from functools import lru_cache

from rapidfuzz import fuzz, process

from .config import ROOT


@lru_cache
def vocabulary():
    return json.loads((ROOT / "data/skills.json").read_text())


# These names are also ordinary words or letters. Require a skill-list entry
# or a nearby technical cue, rather than matching them anywhere in prose.
SHORT_NAMES = {"r": "R", "excel": "Excel", "spark": "Spark", "go": "Go"}


def contextual_name(text, name):
    for match in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I):
        before, after = text[: match.start()], text[match.end() :]
        entry = re.split(r"[,;|/•:\n]", before)[-1].strip(" -")
        tail = re.split(r"[,;|/•:\n]", after)[0].strip()
        if not entry and not tail:
            return True
        if re.search(r"(?:using|with|in|skills?|programming|knowledge of)\s+$", before, re.I):
            return True
        if re.match(r"\s+(?:programming|language|development|pipelines?|spreadsheets?)\b", after, re.I):
            return True
    return False


def mentions(text):
    """Vocabulary skills named in the text, e.g. "Built Python APIs" -> ["Python"]."""
    clauses = re.split(r";|\bbut\b|[.!?](?:\s|$)", text, flags=re.I)
    text = " ".join(
        clause
        for clause in clauses
        if not re.search(
            r"\b(no experience|not experienced|never used|not proficient|unfamiliar with|"
            r"no knowledge|without experience|not familiar|haven.t used|have not used|"
            r"plan to learn|planning to learn|want to learn|interested in learning|"
            r"no proficiency|not skilled|do not know|don.t know)\b",
            clause,
            re.I,
        )
    )
    return [
        s["label"]
        for s in vocabulary()["skills"]
        if (s["id"] != "react" or re.search(r"React\b|react\.js|reactjs|react native", text))
        and (
            any(re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", text, re.I) for a in s["aliases"])
            or (s["id"] in SHORT_NAMES and contextual_name(text, SHORT_NAMES[s["id"]]))
        )
    ]


def normalize_skill(mention):
    """Map a skill name to its vocabulary label, allowing only near-exact spelling."""
    # This input is already a skill name, not arbitrary prose.
    aliases = {a.casefold(): s["label"] for s in vocabulary()["skills"] for a in [s["label"], *s["aliases"]]}
    if mention.casefold() in aliases:
        return aliases[mention.casefold()], "alias"
    match = process.extractOne(mention.casefold(), aliases.keys(), scorer=fuzz.ratio)
    if match and match[1] >= 94 and len(mention) >= 5:
        return aliases[match[0]], "fuzzy"
    return None, "unmapped"
