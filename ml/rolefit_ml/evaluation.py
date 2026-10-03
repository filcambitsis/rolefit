"""Fixed-protocol leave-one-persona-out experiment; no model-selected final scores."""

from collections import defaultdict

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from rolefit.matching import FEATURE_NAMES

GROUPS = {"coverage": [4, 5, 6], "chunk_similarity": [2, 3], "structural_fit": [7, 8, 9, 10]}


def metrics(ranking, judgments, candidate_count):
    def dcg(grades):
        return sum((2**g - 1) / np.log2(i + 2) for i, g in enumerate(grades))

    ideal = dcg(sorted(judgments.values(), reverse=True)[:10])
    relevant = {j for j, g in judgments.items() if g >= 2}
    return {
        "ndcg10": float(dcg([judgments.get(j, 0) for j in ranking[:10]]) / ideal) if ideal else 0.0,
        "precision5": sum(j in relevant for j in ranking[:5]) / 5,
        "recall25": len(set(ranking[:25]) & relevant) / len(relevant) if relevant else 0.0,
        "recall50": len(set(ranking[:50]) & relevant) / len(relevant) if relevant else 0.0,
        "candidate_count": candidate_count,
        "judged_count": len(judgments),
        "top10_judged": sum(j in judgments for j in ranking[:10]),
        "relevant_judged_count": len(relevant),
    }


def model_scores(train, test, columns):
    x = np.asarray([r["features"] for r in train])[:, columns]
    y = np.asarray([int(r["grade"] >= 2) for r in train])
    if len(set(y)) < 2:
        raise ValueError("Each training split needs both relevant and irrelevant human labels")
    model = make_pipeline(
        StandardScaler(), LogisticRegression(C=1, class_weight="balanced", max_iter=2000, random_state=42)
    )
    model.fit(x, y)
    return model.predict_proba(np.asarray([r["features"] for r in test])[:, columns])[:, 1]


def validate(snapshot, labels):
    if snapshot.get("status") != "human-evaluation" or snapshot.get("vocabulary_status") != "frozen-esco":
        raise ValueError(
            "Research requires human-authored personas and a frozen ESCO vocabulary; demo data is not evidence"
        )
    if len(snapshot["jobs"]) < 200:
        raise ValueError("Corpus gate: at least 200 relevant postings required")
    if len(snapshot["personas"]) != 8:
        raise ValueError("Exactly eight personas required")
    if len(labels) < 250:
        raise ValueError("At least 250 human-graded pairs required")
    if any(label.get("snapshot_hash") != snapshot.get("content_hash") for label in labels):
        raise ValueError("Labels must refer to this exact frozen snapshot hash")
    if any(p.get("origin") != "human-authored" for p in snapshot["personas"]):
        raise ValueError("Persona provenance has not passed the human-authorship gate")
    if any(label.get("source") != "human" or not label.get("annotator") for label in labels):
        raise ValueError("All grades require a human source and annotator identity")
    if any(type(label.get("grade")) is not int or not 0 <= label["grade"] <= 3 for label in labels):
        raise ValueError("Grades must be integers 0 through 3")
    if len({(label["persona_id"], label["job_id"]) for label in labels}) != len(labels):
        raise ValueError("Duplicate labels detected")
    candidates = {(r["persona_id"], r["job_id"]) for r in snapshot["pairs"]}
    if any((label["persona_id"], label["job_id"]) not in candidates for label in labels):
        raise ValueError("Labels contain a pair outside the frozen eligible candidates")
    if any(
        len(r["features"]) != len(FEATURE_NAMES) or not np.isfinite(r["features"]).all()
        for r in snapshot["pairs"]
    ):
        raise ValueError("Invalid feature vector")
    for persona in snapshot["personas"]:
        if sum(r["persona_id"] == persona["id"] for r in snapshot["pairs"]) < 100:
            raise ValueError(f"Persona {persona['id']} has fewer than 100 eligible jobs")


def run(snapshot, labels, strict=True):
    if strict:
        validate(snapshot, labels)
    judgments = {(label["persona_id"], label["job_id"]): label["grade"] for label in labels}
    rows = [{**r, "grade": judgments.get((r["persona_id"], r["job_id"]))} for r in snapshot["pairs"]]
    per_persona, missing = [], set()
    curves = defaultdict(list)
    for persona in snapshot["personas"]:
        pid = persona["id"]
        train = [r for r in rows if r["persona_id"] != pid and r["grade"] is not None]
        test = [r for r in rows if r["persona_id"] == pid]
        judged = {r["job_id"]: r["grade"] for r in test if r["grade"] is not None}

        def order(scores):
            return [
                r["job_id"]
                for r, s in sorted(zip(test, scores), key=lambda pair: (-float(pair[1]), pair[0]["job_id"]))
            ]

        ranked = {method: order([r[method] for r in test]) for method in ["bm25", "dense", "hybrid"]}
        ranked["feature"] = order(model_scores(train, test, list(range(len(FEATURE_NAMES)))))
        for group, indices in GROUPS.items():
            ranked["without_" + group] = order(
                model_scores(train, test, [i for i in range(len(FEATURE_NAMES)) if i not in indices])
            )
        for ranking in ranked.values():
            missing.update((pid, j) for j in ranking[:10] if j not in judged)
        results = {method: metrics(ranking, judged, len(test)) for method, ranking in ranked.items()}
        per_persona.append({"persona_id": pid, "metrics": results})
        # Learning curve samples training PERSONAS, never fragments of the held-out query.
        training_ids = sorted({r["persona_id"] for r in train})
        rng = np.random.default_rng(42)
        rng.shuffle(training_ids)
        for n in sorted(set([2, 4, len(training_ids)])):
            subset = [r for r in train if r["persona_id"] in training_ids[:n]]
            if len({r["grade"] >= 2 for r in subset}) < 2:
                continue
            ranking = order(model_scores(subset, test, list(range(len(FEATURE_NAMES)))))
            missing.update((pid, j) for j in ranking[:10] if j not in judged)
            curves[n].append(
                {
                    "persona_id": pid,
                    "training_labels": len(subset),
                    "ndcg10": metrics(ranking, judged, len(test))["ndcg10"],
                }
            )
    if strict and missing:
        return {
            "status": "needs-additional-judgments",
            "required_pairs": [{"persona_id": p, "job_id": j} for p, j in sorted(missing)],
            "conclusion": f"Grade {len(missing)} additional top-10 pairs before reporting the experiment.",
            "results": None,
        }
    methods = list(per_persona[0]["metrics"])
    aggregate = {
        method: {
            key: float(np.mean([p["metrics"][method][key] for p in per_persona]))
            for key in ["ndcg10", "precision5", "recall25", "recall50"]
        }
        for method in methods
    }
    best = max(["bm25", "dense", "hybrid"], key=lambda m: aggregate[m]["ndcg10"])
    deltas = [p["metrics"]["feature"]["ndcg10"] - p["metrics"][best]["ndcg10"] for p in per_persona]
    for p, d in zip(per_persona, deltas):
        p["delta_vs_best_baseline"] = d
    delta = float(np.mean(deltas))
    boot = np.random.default_rng(42).choice(deltas, size=(2000, len(deltas)), replace=True).mean(axis=1)
    ceiling = all(aggregate[m]["ndcg10"] > 0.9 for m in ["bm25", "dense", "hybrid", "feature"])
    supported = delta >= 0.05 and not ceiling and strict
    conclusion = f"Feature ranker nDCG@10 {aggregate['feature']['ndcg10']:.3f}; best baseline {best} {aggregate[best]['ndcg10']:.3f}; delta {delta:+.3f}; improved on {sum(d > 0 for d in deltas)}/{len(deltas)} personas. Hypothesis {'supported' if supported else 'not supported'} at the pre-registered +0.05 threshold."
    if ceiling:
        conclusion = (
            "Ceiling effect: deepen the pool with confusable postings before drawing conclusions. "
            + conclusion
        )
    if not strict:
        conclusion = "SYNTHETIC PIPELINE CHECK ONLY. No scientific conclusion. " + conclusion
    return {
        "status": "complete"
        if strict and not ceiling
        else "needs-deeper-pool"
        if ceiling
        else "synthetic-check",
        "conclusion": conclusion,
        "best_baseline": best,
        "delta": delta,
        "bootstrap_ci95": np.quantile(boot, [0.025, 0.975]).tolist(),
        "results": aggregate,
        "per_persona": per_persona,
        "learning_curve": dict(curves),
        "recall_note": "Recall is over judged relevant jobs in the frozen pool, not all relevant jobs in the corpus. Unjudged documents are not evidence of irrelevance.",
        "protocol": {
            "seed": 42,
            "C": 1,
            "threshold": 0.05,
            "splits": "leave-one-persona-out",
            "features": FEATURE_NAMES,
        },
    }
