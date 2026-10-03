"""Import an official ESCO English skills CSV and an explicitly reviewed URI selection."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("csv", type=Path, help="Official ESCO skills_en.csv export")
parser.add_argument(
    "uris", type=Path, help="Reviewed one-URI-per-line AI/data/technology selection (300–500 entries)"
)
parser.add_argument("--version", required=True, help="Official ESCO release version")
parser.add_argument("--output", type=Path, default=Path("data/skills.json"))
args = parser.parse_args()
selected = {
    line.strip() for line in args.uris.read_text().splitlines() if line.strip() and not line.startswith("#")
}
if not 300 <= len(selected) <= 500:
    parser.error("Select 300–500 reviewed ESCO concept URIs before freezing")
with args.csv.open(encoding="utf-8-sig", newline="") as stream:
    rows = [r for r in csv.DictReader(stream) if r["conceptUri"] in selected]
if len(rows) != len(selected):
    parser.error("Some selected URIs are absent from the supplied official export")
value = {
    "version": args.version,
    "status": "frozen-esco",
    "source": "https://esco.ec.europa.eu/en/use-esco/download",
    "source_hash": hashlib.sha256(args.csv.read_bytes()).hexdigest(),
    "skills": [
        {
            "id": r["conceptUri"],
            "label": r["preferredLabel"],
            "aliases": list(dict.fromkeys([r["preferredLabel"]] + r.get("altLabels", "").splitlines())),
        }
        for r in rows
    ],
}
args.output.write_text(json.dumps(value, indent=2))
print(f"Frozen {len(rows)} ESCO skills; commit vocabulary and selection before evaluation")
