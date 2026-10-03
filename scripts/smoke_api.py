"""Exercise a local development API with a clearly synthetic sample CV."""

import json
from pathlib import Path
import httpx

base = "http://127.0.0.1:8000"
fixture = json.loads(Path("data/personas/ml-engineer.json").read_text())
with httpx.Client(base_url=base, timeout=90) as client:
    assert client.get("/health").status_code == 200
    response = client.post(
        "/cv", files={"file": ("Sample CV - replace with your own.txt", fixture["text"], "text/plain")}
    )
    response.raise_for_status()
    parsed = response.json()
    assert client.put("/preferences", json=fixture["preferences"]).status_code == 200
    response = client.post("/matches")
    response.raise_for_status()
    jobs = response.json()["jobs"]
    assert len(jobs) >= 200
    for job in jobs:
        for requirement in job["requirements"]:
            if requirement["status"] == "met":
                ev = requirement["evidence"]
                assert fixture["text"][ev["start"] : ev["end"]] == ev["quote"]
    job = jobs[0]
    detail = client.get("/jobs/" + job["id"])
    detail.raise_for_status()
    assert detail.json()["description"]
    decision = client.put("/jobs/" + job["id"] + "/decision", json={"state": "saved"})
    decision.raise_for_status()
    assert job["id"] in client.get("/me").json()["saved"]
    client.put("/jobs/" + job["id"] + "/decision", json={"state": "none"}).raise_for_status()
    print(
        json.dumps(
            {
                "upload": "passed",
                "preferences": "passed",
                "matching": "passed",
                "candidate_count": len(jobs),
                "evidence_invariant": "passed",
                "detail": "passed",
                "save": "passed",
                "verification_failure_rate": parsed["failure_rate"],
            }
        )
    )
