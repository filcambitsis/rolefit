import json
import re
from functools import lru_cache

from rapidfuzz import fuzz, process

from .config import ROOT


@lru_cache
def vocabulary():
    return json.loads((ROOT / "data/skills.json").read_text())


def mentions(text):
    """Vocabulary skills named in the text, e.g. "Built Python APIs" -> ["Python"]."""
    # Negated lines ("no experience with Java") never count as evidence.
    if re.search(
        r"\b(no experience|not experienced|never used|not proficient|unfamiliar with)\b", text, re.I
    ):
        return []
    return [
        s["label"]
        for s in vocabulary()["skills"]
        if any(re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", text, re.I) for a in s["aliases"])
    ]


def normalize_skill(mention):
    """Map a skill name to its vocabulary label, allowing only near-exact spelling."""
    aliases = {a.casefold(): s["label"] for s in vocabulary()["skills"] for a in s["aliases"]}
    if mention.casefold() in aliases:
        return aliases[mention.casefold()], "alias"
    match = process.extractOne(mention.casefold(), aliases.keys(), scorer=fuzz.ratio)
    if match and match[1] >= 94 and len(mention) >= 5:
        return aliases[match[0]], "fuzzy"
    return None, "unmapped"
