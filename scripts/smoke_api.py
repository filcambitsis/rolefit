"""Check the main flow against a running local API, using the fictional sample CV.

Usage: start the API (make run-api), then run .venv/bin/python scripts/smoke_api.py
"""

import json
import os
from pathlib import Path

import httpx

BASE = os.environ.get("API_URL", "http://127.0.0.1:8000")
CV_TEXT = (Path(__file__).resolve().parents[1] / "data/sample-cv.txt").read_text()

with httpx.Client(base_url=BASE, timeout=90) as client:
    assert client.get("/health").status_code == 200

    existing = client.get("/me")
    existing.raise_for_status()
    if existing.json()["cv"] is not None:
        raise SystemExit("Use a disposable database: this workspace already contains a CV.")

    # 1. Upload the CV.
    response = client.post("/cv", files={"file": ("sample-cv.txt", CV_TEXT, "text/plain")})
    response.raise_for_status()
    parsed = response.json()

    # 2. Reset preferences and run matching.
    client.put("/preferences", json={}).raise_for_status()
    response = client.post("/matches")
    response.raise_for_status()
    jobs = response.json()["jobs"]
    assert jobs, "No jobs matched; run make crawl first"

    # 3. Every "met" requirement must point at an exact passage of the CV.
    for job in jobs:
        for requirement in job["requirements"]:
            if requirement["status"] == "met":
                ev = requirement["evidence"]
                assert CV_TEXT[ev["start"] : ev["end"]] == ev["quote"]

    # 4. Job details, then save and unsave the top job.
    job_id = jobs[0]["id"]
    client.get("/jobs/" + job_id).raise_for_status()
    client.put(f"/jobs/{job_id}/decision", json={"state": "saved"}).raise_for_status()
    assert job_id in client.get("/me").json()["saved"]
    client.put(f"/jobs/{job_id}/decision", json={"state": "none"}).raise_for_status()

    client.delete("/cv").raise_for_status()

    print(
        json.dumps(
            {
                "evidence_passages": len(parsed["evidence"]),
                "jobs_matched": len(jobs),
                "top_job": f"{jobs[0]['title']} at {jobs[0]['company']} ({jobs[0]['score']}%)",
                "result": "passed",
            },
            indent=2,
        )
    )
