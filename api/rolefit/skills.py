import json
import re
from functools import lru_cache

from rapidfuzz import fuzz, process

from .config import ROOT


@lru_cache
def vocabulary():
    return json.loads((ROOT / "data/skills.json").read_text())


def mentions(text):
    if re.search(
        r"\b(no experience|not experienced|never used|not proficient|unfamiliar with)\b", text, re.I
    ):
        return []
    return [
        s["label"]
        for s in vocabulary()["skills"]
        if any(re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", text, re.I) for a in s["aliases"])
    ]


def normalize_skill(mention, embedder=None):
    aliases = {a.casefold(): s["label"] for s in vocabulary()["skills"] for a in s["aliases"]}
    if mention.casefold() in aliases:
        return aliases[mention.casefold()], "alias"
    match = process.extractOne(mention.casefold(), aliases.keys(), scorer=fuzz.ratio)
    if match and match[1] >= 94 and len(mention) >= 5:
        return aliases[match[0]], "fuzzy"
    if embedder:
        import numpy as np

        labels = [s["label"] for s in vocabulary()["skills"]]
        vectors = embedder.embed(labels)
        scores = vectors @ embedder.embed([mention])[0]
        best = int(np.argmax(scores))
        if scores[best] >= 0.88:
            return labels[best], "embedding"
    return None, "unmapped"
