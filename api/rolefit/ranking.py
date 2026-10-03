import math
import re
from collections import Counter


def tokenize(text):
    # Lowercase words, keeping names like "c++" and "c#" intact.
    return re.findall(r"[a-z0-9]+(?:[+#][+#]?)?", text.lower())


def bm25_scores(documents, query, k1=1.2, b=0.75):
    """Score each document against the query with Okapi BM25.

    Used only as a tiebreaker: jobs whose text shares more words with the CV
    come first when their requirement coverage is equal.
    """
    docs = [Counter(tokenize(d)) for d in documents]
    if not docs:
        return []
    lengths = [sum(d.values()) for d in docs]
    average = max(sum(lengths) / len(docs), 1)
    # How many documents contain each word (rare words count for more).
    doc_freq = Counter(word for d in docs for word in d)

    scores = [0.0] * len(docs)
    for word in set(tokenize(query)):
        idf = math.log(1 + (len(docs) - doc_freq[word] + 0.5) / (doc_freq[word] + 0.5))
        for i, doc in enumerate(docs):
            freq = doc[word]
            if freq:
                norm = k1 * (1 - b + b * lengths[i] / average)
                scores[i] += idf * freq * (k1 + 1) / (freq + norm)
    return scores
