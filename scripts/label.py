"""Local, keyboard-first human annotation. Never pre-fills model-generated grades."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, default=ROOT / "data/evaluation/snapshot.json")
    parser.add_argument("--labels", type=Path, default=ROOT / "data/evaluation/labels.json")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--additional", type=Path, help="Results file containing second-round required_pairs")
    args = parser.parse_args()
    if not args.snapshot.exists():
        parser.error("No frozen snapshot. Create human personas, run embeddings, then rolefit freeze.")
    from rolefit_ml.dataset import pool

    snapshot = json.loads(args.snapshot.read_text())
    pairs = json.loads(args.additional.read_text())["required_pairs"] if args.additional else pool(snapshot)
    known = {(p["persona_id"], p["job_id"]) for p in pairs}
    labels = json.loads(args.labels.read_text()) if args.labels.exists() else []
    # Raw descriptions are read from the private local DB; never included in public snapshot.
    from rolefit.db import SessionLocal
    from rolefit.models import Job

    with SessionLocal() as db:
        descriptions = {
            j["id"]: (
                db.get(Job, j["id"]).description
                if db.get(Job, j["id"])
                else "Original posting not available locally. Re-fetch and check its frozen hash before grading."
            )
            for j in snapshot["jobs"]
        }

    class Handler(BaseHTTPRequestHandler):
        def send_json(self, value, status=200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(json.dumps(value).encode())

        def do_GET(self):
            if self.path == "/data":
                self.send_json(
                    {
                        "personas": snapshot["personas"],
                        "jobs": [{**j, "description": descriptions[j["id"]]} for j in snapshot["jobs"]],
                        "pairs": pairs,
                        "labels": labels,
                    }
                )
            elif self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write((ROOT / "scripts/label.html").read_bytes())
            else:
                self.send_json({"error": "Not found"}, 404)

        def do_POST(self):
            origin = self.headers.get("Origin", "")
            if (
                urlparse(origin).netloc not in (f"127.0.0.1:{args.port}", f"localhost:{args.port}")
                or self.headers.get("Content-Type") != "application/json"
                or self.path != "/grade"
            ):
                self.send_json({"error": "Rejected origin or request"}, 403)
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 10000:
                    raise ValueError("Invalid size")
                value = json.loads(self.rfile.read(length))
                if (
                    (value["persona_id"], value["job_id"]) not in known
                    or type(value["grade"]) is not int
                    or not 0 <= value["grade"] <= 3
                    or not value.get("annotator", "").strip()
                ):
                    raise ValueError("Invalid label")
                from datetime import datetime, timezone

                label = {k: value[k] for k in ["persona_id", "job_id", "grade", "annotator"]}
                label.update(
                    source="human",
                    note=str(value.get("note", ""))[:2000],
                    graded_at=datetime.now(timezone.utc).isoformat(),
                    snapshot_hash=snapshot.get("content_hash"),
                )
                labels[:] = [
                    r
                    for r in labels
                    if (r["persona_id"], r["job_id"]) != (value["persona_id"], value["job_id"])
                ] + [label]
                temporary = args.labels.with_suffix(".tmp")
                temporary.write_text(json.dumps(labels, indent=2))
                temporary.replace(args.labels)
                self.send_json({"saved": True})
            except (ValueError, KeyError):
                self.send_json({"error": "Invalid label"}, 422)

    print(f"Human labeling workspace: http://127.0.0.1:{args.port}")
    HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
