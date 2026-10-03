import math
import re
from collections import Counter

import numpy as np


def tokenize(text):
    return re.findall(r"[a-z0-9]+(?:[+#][+#]?)?", text.lower())


class BM25:
    """Okapi BM25, k1=1.2 and b=.75. No ts_rank approximation."""

    def __init__(self, documents):
        self.documents = [Counter(tokenize(d)) for d in documents]
        self.lengths = [sum(d.values()) for d in self.documents]
        self.average = np.mean(self.lengths) if self.lengths else 1
        self.df = Counter(t for doc in self.documents for t in doc)

    def score(self, query):
        n = len(self.documents)
        scores = np.zeros(n)
        for term in set(tokenize(query)):
            idf = math.log(1 + (n - self.df[term] + 0.5) / (self.df[term] + 0.5))
            for i, doc in enumerate(self.documents):
                frequency = doc[term]
                if frequency:
                    scores[i] += (
                        idf
                        * frequency
                        * 2.2
                        / (frequency + 1.2 * (0.25 + 0.75 * self.lengths[i] / max(self.average, 1)))
                    )
        return scores


def rrf(*rankings, k=60):
    scores = Counter()
    for ranking in rankings:
        for rank, job_id in enumerate(ranking, 1):
            scores[job_id] += 1 / (k + rank)
    return scores


def rank(ids, scores):
    return sorted(zip(ids, map(float, scores)), key=lambda item: (-item[1], item[0]))


def retrieve(method, jobs, cv_text, evidence_vectors=None):
    ids = [j.id for j in jobs]
    lexical = BM25([j.title + "\n" + j.description for j in jobs]).score(cv_text)
    if method == "bm25":
        return rank(ids, lexical)
    if evidence_vectors is None or len(evidence_vectors) == 0 or any(j.embedding is None for j in jobs):
        raise ValueError(
            "Dense/hybrid retrieval requires real bge embeddings for every candidate and CV evidence"
        )
    pooled = np.mean(evidence_vectors, axis=0)
    pooled /= max(float(np.linalg.norm(pooled)), 1e-9)
    dense = rank(ids, np.array([j.embedding for j in jobs]) @ pooled)
    if method == "dense":
        return dense
    if method == "hybrid":
        scores = rrf([i for i, _ in rank(ids, lexical)], [i for i, _ in dense])
        return rank(ids, [scores[i] for i in ids])
    raise ValueError(f"Unknown retrieval method {method}")
