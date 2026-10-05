"""Generate fictional demo results with the same extraction and matching as the API."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from rolefit.extraction import extract_cv, extract_requirements
from rolefit.matching import match_requirement, requirement_score
from rolefit.normalization import FAMILIES, career_level

ROOT = Path(__file__).resolve().parents[1]


def snapshot():
    raw = (ROOT / "data/sample-cv.txt").read_text()
    evidence = [dict(id=f"ev-{i}", **row) for i, row in enumerate(extract_cv(raw)[0])]
    rows = [SimpleNamespace(**row) for row in evidence]
    jobs = []
    for i, (company, title, location, country, family, workplace, required, preferred) in enumerate(
        json.loads((ROOT / "data/demo-jobs.json").read_text())
    ):
        description = "Requirements\n" + "\n".join(f"Experience with {s}." for s in required)
        description += "\nNice to have\n" + "\n".join(f"Experience with {s}." for s in preferred)
        requirements = [
            match_requirement(SimpleNamespace(id=f"r-{i}-{n}", **req), rows, raw)
            for n, req in enumerate(extract_requirements(description))
        ]
        employment = "part-time" if company == "Aperture" else "full-time"
        jobs.append(
            dict(
                id=f"demo-{i}",
                company=company,
                title=title,
                location=location,
                countries=[country],
                family=family,
                employment=employment,
                career_level=career_level(title, employment),
                workplace=workplace,
                provider="sample",
                url="",
                score=requirement_score(requirements),
                requirements=requirements,
                first_seen="2026-09-14",
                description=description,
            )
        )
    return dict(families=FAMILIES, evidence=evidence, jobs=jobs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "web/lib/demo-data.json"
    content = json.dumps(snapshot(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not path.exists() or path.read_text() != content:
            raise SystemExit("Demo fixture is stale. Run make demo-data.")
    else:
        path.write_text(content)
