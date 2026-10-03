from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import func, select

from rolefit.extraction import extract_cv, extract_requirements, parse_file, verified_span
from rolefit.ingestion import reconcile
from rolefit.matching import match_requirement, years_of_experience
from rolefit.models import Evidence, Job, User
from rolefit.normalization import employment, family
from rolefit.ranking import bm25_scores

CV_TEXT = "Alex Test\nEXPERIENCE\nBuilt Python services and SQL reporting pipelines for a warehouse.\nEDUCATION\nMSc Computer Science\n"


def test_spans_and_fabrication():
    rows, failures, total = extract_cv(CV_TEXT)
    assert failures == 0 and total > 0
    for row in rows:
        assert CV_TEXT[row["start"] : row["end"]] == row["quote"]
    assert verified_span(CV_TEXT, "I deployed Kubernetes") is None
    req = SimpleNamespace(
        id="r", skill="Python", min_years=None, category="skill", text="Python", quote="Python", required=True
    )
    forged = SimpleNamespace(id="e", start=0, end=6, quote="Python", skills=["Python"], section="skills")
    assert match_requirement(req, [forged], CV_TEXT)["status"] == "missing"


def test_cv_flow_and_user_isolation(client, db, job):
    response = client.post("/cv", files={"file": ("cv.txt", CV_TEXT, "text/plain")})
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["evidence"]) > 0 and data["verification_failures"] == 0
    assert client.get("/me", headers={"X-Test-User": "bob"}).json()["cv"] is None
    assert client.post("/matches", headers={"X-Test-User": "bob"}).status_code == 409
    matches = client.post("/matches").json()["jobs"]
    assert len(matches) == 1
    matched = [r for r in matches[0]["requirements"] if r["status"] == "met"]
    assert {r["skill"] for r in matched} == {"Python", "SQL"}
    for row in matched:
        span = row["evidence"]
        assert CV_TEXT[span["start"] : span["end"]] == span["quote"]
    assert client.put(f"/jobs/{job.id}/decision", json={"state": "saved"}).status_code == 200
    assert client.get("/me").json()["saved"] == [job.id]
    assert client.get("/me", headers={"X-Test-User": "bob"}).json()["saved"] == []
    assert client.delete("/cv", headers={"X-Test-User": "bob"}).status_code == 204
    assert client.get("/me").json()["cv"] is not None
    assert client.delete("/cv").status_code == 204
    assert db.scalar(select(func.count()).select_from(Evidence)) == 0
    assert client.post("/matches").status_code == 409


def test_hard_filters_unknown_country_and_closed(client, job, db):
    client.post("/cv", files={"file": ("cv.txt", CV_TEXT)})
    client.put("/preferences", json={"countries": ["US"]})
    assert client.post("/matches").json()["jobs"] == []
    client.put("/preferences", json={"countries": ["NL"]})
    assert len(client.post("/matches").json()["jobs"]) == 1
    job.countries = []
    db.commit()
    assert client.post("/matches").json()["jobs"] == []
    client.put("/preferences", json={})
    job.is_open = False
    db.commit()
    assert client.post("/matches").json()["jobs"] == []
    assert client.put("/preferences", json={"employment": []}).status_code == 422


def test_replacement_and_invalid_upload(client, db):
    assert client.post("/cv", files={"file": ("cv.txt", CV_TEXT)}).status_code == 200
    previous = client.get("/me").json()["cv"]["id"]
    assert client.post("/cv", files={"file": ("bad.pdf", b"not a pdf")}).status_code == 422
    assert client.get("/me").json()["cv"]["id"] == previous
    assert client.post("/cv", files={"file": ("cv2.txt", CV_TEXT + "More text.")}).status_code == 200
    assert client.get("/me").json()["cv"]["id"] != previous


def test_ingestion_idempotent_and_closure_grace(db, job):
    source = {"provider": "greenhouse", "board": "test"}
    timestamp = datetime.now(timezone.utc)
    record = {
        c.name: getattr(job, c.name)
        for c in Job.__table__.columns
        if c.name not in {"id", "first_seen", "last_seen", "is_open", "duplicate_of"}
    }
    first = reconcile(db, source, [record], timestamp)
    db.commit()
    second = reconcile(db, source, [record], timestamp)
    db.commit()
    assert first == second == {}
    assert db.scalar(select(func.count()).select_from(Job)) == 1
    reconcile(db, source, [], timestamp + timedelta(hours=1))
    assert job.is_open
    reconcile(db, source, [], timestamp + timedelta(hours=25))
    assert not job.is_open


def test_employment_provenance_and_role_rules():
    assert employment("FullTime", "") == ("full-time", "structured")
    assert employment("Part-time", "") == ("part-time", "structured")
    assert employment("", "Internship in data") == ("internship", "inferred")
    assert employment("", "Permanent employee") == ("unknown", "unknown")
    assert family("Senior Machine Learning Engineer") == "ML Engineer"
    assert family("Account Executive") is None


def test_overlapping_experience_not_double_counted():
    rows = [
        SimpleNamespace(section="experience", quote="Jan 2020 – Dec 2022"),
        SimpleNamespace(section="experience", quote="Jan 2021 – Dec 2023"),
        SimpleNamespace(section="education", quote="Jan 2010 – Dec 2019"),
    ]
    assert years_of_experience(rows) == 4


def test_requirements_separate_preferred():
    rows = extract_requirements(
        "Requirements\nExperience with Python.\nNice to have\nExperience with Kubernetes."
    )
    assert [(r["skill"], r["required"]) for r in rows] == [("Python", True), ("Kubernetes", False)]


def test_pdf_two_columns_and_docx():
    import io
    import pymupdf
    from docx import Document

    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((30, 50), "SKILLS\nPython and SQL experience\nDocker services deployment", fontsize=11)
    page.insert_text(
        (330, 50),
        "EXPERIENCE\nBuilt reporting pipelines for clients\nMSc Computer Science graduate",
        fontsize=11,
    )
    text = parse_file(pdf.tobytes(), "two-columns.pdf")
    assert "Python and SQL" in text and "Built reporting" in text
    document = Document()
    document.add_paragraph(CV_TEXT)
    stream = io.BytesIO()
    document.save(stream)
    assert "Python" in parse_file(stream.getvalue(), "cv.docx")


def test_bm25_prefers_documents_sharing_words():
    scores = bm25_scores(["Python SQL", "Retail sales"], "Python")
    assert scores[0] > 0 and scores[1] == 0
    assert bm25_scores([], "Python") == []


def test_ranking_and_retired_family_preferences(client, db, job):
    client.post("/cv", files={"file": ("cv.txt", CV_TEXT)})
    # Preferences saved before a role family was removed must not break matching.
    db.get(User, "alice").preferences = {"families": ["AI/Technology Consultant"]}
    db.commit()
    jobs = client.post("/matches").json()["jobs"]
    assert [j["id"] for j in jobs] == [job.id]
    assert family("AI & Technology Consultant") is None
