"""Export the selected method as inert JSON, never executable pickle artifacts."""

import hashlib
import json

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from rolefit.config import ROOT
from rolefit.matching import FEATURE_NAMES

ARTIFACT = ROOT / "ml/models/winner.json"


def export(snapshot, labels, report):
    if report.get("status") != "complete":
        raise ValueError(
            "A completed, non-ceiling-effect human evaluation is required before selecting a winner"
        )
    method = max(["bm25", "dense", "hybrid", "feature"], key=lambda m: report["results"][m]["ndcg10"])
    artifact = {
        "method": method,
        "feature_names": FEATURE_NAMES,
        "snapshot_hash": snapshot["content_hash"],
        "evaluation_hash": hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest(),
    }
    if method == "feature":
        judgments = {(label["persona_id"], label["job_id"]): label["grade"] for label in labels}
        rows = [r for r in snapshot["pairs"] if (r["persona_id"], r["job_id"]) in judgments]
        model = make_pipeline(
            StandardScaler(), LogisticRegression(C=1, class_weight="balanced", max_iter=2000, random_state=42)
        )
        model.fit(
            [r["features"] for r in rows], [int(judgments[(r["persona_id"], r["job_id"])] >= 2) for r in rows]
        )
        scaler, ranker = model.steps[0][1], model.steps[1][1]
        artifact.update(
            mean=scaler.mean_.tolist(),
            scale=scaler.scale_.tolist(),
            coefficients=ranker.coef_[0].tolist(),
            intercept=float(ranker.intercept_[0]),
        )
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(artifact, indent=2))
    return artifact


def score(artifact, rows):
    if artifact["feature_names"] != FEATURE_NAMES:
        raise ValueError("Ranker feature schema mismatch")
    x = np.asarray(rows)
    logits = ((x - artifact["mean"]) / artifact["scale"]) @ np.asarray(artifact["coefficients"]) + artifact[
        "intercept"
    ]
    return 1 / (1 + np.exp(-np.clip(logits, -50, 50)))
