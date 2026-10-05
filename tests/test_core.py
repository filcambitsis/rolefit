from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from sqlalchemy import func, select

from rolefit.extraction import extract_cv, extract_requirements, parse_file, verified_span
from rolefit.ingestion import reconcile
from rolefit.matching import match_requirement
from rolefit.models import Evidence, Job, User
from rolefit.normalization import countries, employment, family
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
    assert match_requirement(req, [forged], CV_TEXT)["status"] == "not_verified"


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
    assert len(client.post("/matches").json()["jobs"]) == 1
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
    assert family("AI & Technology Consultant") == "AI Consultant"


def test_skill_names_and_distinct_technologies():
    from rolefit.skills import mentions, normalize_skill

    assert set(mentions("Python, R, SQL, Excel, Spark, Go")) == {"Python", "R", "SQL", "Excel", "Spark", "Go"}
    assert mentions("We excel at helping ideas spark and go further.") == []
    for name in ["R", "Excel", "Spark", "Go", "LightGBM", "Hive", "OpenSearch"]:
        assert normalize_skill(name)[0] == name
    assert mentions("Built a LightGBM model with Apache Hive and OpenSearch.") == [
        "LightGBM",
        "Hive",
        "OpenSearch",
    ]
    req = SimpleNamespace(
        id="r",
        skill="XGBoost",
        min_years=None,
        category="skill",
        text="XGBoost",
        quote="XGBoost",
        required=True,
    )
    raw = "Built a LightGBM model."
    evidence, _, _ = extract_cv(raw)
    rows = [SimpleNamespace(id="e", **row) for row in evidence]
    assert match_requirement(req, rows, raw)["status"] == "not_verified"


def test_common_cv_headings_and_short_skill_lines():
    raw = (
        "Professional Experience\nBuilt Python services for clients.\n"
        "Key Projects\nBuilt a Flask application.\n"
        "Skills & Interests\nR\nExcel\n"
        "Leadership & Activities\nOrganised community activities."
    )
    rows, failures, _ = extract_cv(raw)
    assert failures == 0
    assert [r["section"] for r in rows] == ["experience", "projects", "skills", "skills", "other"]
    assert rows[2]["skills"] == ["R"]
    assert rows[3]["skills"] == ["Excel"]


@pytest.mark.parametrize("entrypoint", ["profile", "matches", "details"])
def test_old_cv_refreshes_without_reupload(client, db, job, entrypoint):
    from rolefit.extraction import PROMPT_VERSION
    from rolefit.models import CV

    raw = "Professional Experience\nBuilt Keras models for clients.\nSkills\nR"
    client.post("/cv", files={"file": ("cv.txt", raw)})
    cv = db.scalar(select(CV))
    cv.prompt_version = "evidence-v2"
    for row in db.scalars(select(Evidence)):
        row.skills = []
    db.commit()
    if entrypoint == "matches":
        assert client.post("/matches").status_code == 200
    elif entrypoint == "details":
        assert client.get(f"/jobs/{job.id}").status_code == 200
    result = client.get("/me").json()
    assert {"Keras", "R"} <= {s for e in result["evidence"] for s in e["skills"]}
    assert cv.prompt_version == PROMPT_VERSION
    assert all(raw[e["start"] : e["end"]] == e["quote"] for e in result["evidence"])
    assert client.post("/matches").status_code == 200


def test_legacy_cache_cleanup_and_user_isolation(client, db):
    from rolefit.models import CV, ExtractionCache

    for action in ["replace", "delete_cv", "delete_user"]:
        client.post("/cv", files={"file": ("cv.txt", CV_TEXT)})
        cv = db.scalar(select(CV).where(CV.user_id == "alice"))
        key = "legacy-" + action
        db.add(
            ExtractionCache(
                key=key,
                scope="adjudication:" + cv.id,
                model_version="old",
                prompt_version="evidence-v1",
                payload={"evidence_quote": "Private passage"},
            )
        )
        db.commit()
        if action == "replace":
            db.add(
                ExtractionCache(
                    key="other-user",
                    scope="bob",
                    model_version="old",
                    prompt_version="evidence-v1",
                    payload={},
                )
            )
            db.commit()
            response = client.post("/cv", files={"file": ("new.txt", CV_TEXT + "Updated.")})
        else:
            response = client.delete("/cv" if action == "delete_cv" else "/me")
        assert response.status_code in (200, 204)
        assert db.get(ExtractionCache, key) is None
        assert db.get(ExtractionCache, "other-user") is not None


@pytest.mark.parametrize(
    "rows, expected",
    [
        ([], None),
        ([(True, "met")], 100),
        ([(False, "met")], 100),
        ([(True, "not_verified")], 0),
        ([(True, "met"), (False, "not_verified")], 85),
        ([(True, "met"), (True, "not_verified"), (False, "not_verified")], 43),
        ([(True, "met"), (True, "not_verified")], 50),
        ([(False, "met"), (False, "not_verified")], 50),
    ],
)
def test_requirement_score_available_groups(rows, expected):
    from rolefit.matching import requirement_score

    assert (
        requirement_score([{"required": required, "status": status} for required, status in rows]) == expected
    )


def test_no_requirements_has_no_score(client, db, job):
    client.post("/cv", files={"file": ("cv.txt", CV_TEXT)})
    job.description = "We are a friendly team with good benefits."
    db.commit()
    result = client.post("/matches").json()["jobs"][0]
    assert result["score"] is None
    assert result["requirements"] == []


def test_requirement_sections_and_manual_constraints():
    text = (
        "About us\nWe have experience with Python.\n"
        "You might thrive in this role if:\n"
        "PhD or Master's degree in Computer Science.\n"
        "5 years of professional experience in data science.\n"
        "Published research at major conferences.\n"
        "Proficiency in Python.\n"
        "Preferred qualifications\nExperience with Docker.\n"
        "About Example\nOur company has experience with Java."
    )
    rows = extract_requirements(text)
    assert [r["category"] for r in rows] == ["education", "experience", "other", "skill", "skill"]
    assert rows[-1]["required"] is False
    assert {r["skill"] for r in rows} == {None, "Python", "Docker"}
    raw = "Mar 2010 - Present"
    evidence = [SimpleNamespace(id="e", quote=raw, start=0, end=len(raw), section="experience", skills=[])]
    for row in rows[:2]:
        assert match_requirement(SimpleNamespace(id="r", **row), evidence, raw)["status"] == "not_verified"


def test_negation_and_react_agent():
    from rolefit.skills import mentions

    assert mentions("Built Python tools but no experience with Java.") == ["Python"]
    assert mentions("Never used Docker.") == []
    assert "React" not in mentions("Built a ReAct agent.")
    assert "React" in mentions("Built a React frontend.")


@pytest.mark.parametrize(
    "heading",
    ["Required Qualifications", "It's Important To Us That You Have", "Skills You'll Need to Bring:"],
)
def test_required_heading_variants(heading):
    rows = extract_requirements(
        f"{heading}\n4 years of relevant experience.\nProficiency in Python.\n"
        "It Would Be Great if You Had\nExperience with Docker.\n"
        "Notice\nOur company offers benefits."
    )
    assert [(r["category"], r["required"]) for r in rows] == [
        ("experience", True),
        ("skill", True),
        ("skill", False),
    ]


def test_unreadable_pdf_preserves_existing_cv(client):
    import pymupdf

    client.post("/cv", files={"file": ("cv.txt", CV_TEXT)})
    previous = client.get("/me").json()["cv"]["id"]
    with pymupdf.open() as document:
        document.new_page()
        response = client.post("/cv", files={"file": ("scanned.pdf", document.tobytes())})
    assert response.status_code == 422
    assert client.get("/me").json()["cv"]["id"] == previous


@pytest.mark.parametrize(
    "location, explicit, expected",
    [
        ("Athens, Greece", "", ["GR"]),
        ("Thessaloniki", "", ["GR"]),
        ("Αθήνα, Ελλάδα", "", ["GR"]),
        ("Remote", "GR", ["GR"]),
        ("Athens, Georgia", "US", ["US"]),
        ("Amsterdam, Netherlands", "", ["NL"]),
        ("Remote", "", []),
    ],
)
def test_work_countries(location, explicit, expected):
    assert countries(location, explicit) == expected


@pytest.mark.parametrize("country", ["US", "GR", "DE", None])
def test_netherlands_scope_cannot_be_overridden(client, job, db, country):
    client.post("/cv", files={"file": ("cv.txt", CV_TEXT)})
    client.put(f"/jobs/{job.id}/decision", json={"state": "saved"})
    job.countries = [country] if country else []
    job.workplace = "remote"
    db.commit()
    for selection in [["NL"], ["US"], []]:
        assert client.put("/preferences", json={"countries": selection}).status_code == 200
        assert client.post("/matches").json()["jobs"] == []
    assert client.get(f"/jobs/{job.id}").status_code == 404
    assert client.put(f"/jobs/{job.id}/decision", json={"state": "saved"}).status_code == 404
    assert client.get("/me").json()["saved"] == []
    assert "countries" not in client.get("/me").json()["preferences"]


def test_multilocation_job_available_in_netherlands(client, job, db):
    client.post("/cv", files={"file": ("cv.txt", CV_TEXT)})
    job.countries = ["NL", "DE"]
    db.commit()
    assert len(client.post("/matches").json()["jobs"]) == 1


@pytest.mark.parametrize("heading", ["Must-Have", "What You Will Bring", "What you will need:"])
def test_dutch_feed_requirement_headings(heading):
    rows = extract_requirements(
        f"{heading}\nExperience with Python.\nNice-to-Have\nExperience with Docker.\nWhat we offer\nTraining in SQL and Kubernetes."
    )
    assert any(row["skill"] == "Python" and row["required"] for row in rows)
    assert any(row["skill"] == "Docker" and not row["required"] for row in rows)
    assert not any(row["skill"] in {"SQL", "Kubernetes"} for row in rows)


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Junior Software Engineer", "Software Engineer"),
        ("Senior Data Engineer", "Data Engineer"),
        ("Frontend Developer", "Software Engineer"),
        ("AI Software Engineer", "AI Engineer"),
        ("Account Executive", None),
    ],
)
def test_expanded_role_types(title, expected):
    assert family(title) == expected


@pytest.mark.parametrize(
    "title,employment,expected",
    [
        ("Software Engineer", "full-time", "unknown"),
        ("Junior Developer", "full-time", "junior"),
        ("Senior ML Engineer", "full-time", "senior"),
        ("Staff Data Engineer", "full-time", "lead"),
        ("Medior Software Engineer", "full-time", "mid"),
        ("Research Engineer", "internship", "internship"),
    ],
)
def test_career_level_is_conservative(title, employment, expected):
    from rolefit.normalization import career_level

    assert career_level(title, employment) == expected


def test_career_and_workplace_filters(client, job, db):
    client.post("/cv", files={"file": ("cv.txt", CV_TEXT)})
    job.title = "Junior Software Engineer"
    job.family = "Software Engineer"
    job.workplace = "hybrid"
    db.commit()
    for prefs, count in [
        ({"families": ["Software Engineer"], "career_levels": ["junior"], "workplace": "hybrid"}, 1),
        ({"career_levels": ["senior"]}, 0),
        ({"workplace": "remote"}, 0),
        ({}, 1),
    ]:
        assert client.put("/preferences", json=prefs).status_code == 200
        assert len(client.post("/matches").json()["jobs"]) == count
    job.workplace = "unknown"
    db.commit()
    client.put("/preferences", json={"workplace": "remote"})
    assert client.post("/matches").json()["jobs"] == []
    assert client.put("/preferences", json={"career_levels": ["invented"]}).status_code == 422


@pytest.mark.parametrize(
    "employment,expected", [(["internship"], 1), (["full-time", "internship"], 1), (["full-time"], 0)]
)
def test_internships_follow_employment_not_career_level(client, job, db, employment, expected):
    client.post("/cv", files={"file": ("cv.txt", CV_TEXT)})
    job.title = "Machine Learning Intern"
    job.employment = "internship"
    db.commit()
    assert (
        client.put("/preferences", json={"career_levels": ["junior"], "employment": employment}).status_code
        == 200
    )
    assert len(client.post("/matches").json()["jobs"]) == expected


def test_legacy_internship_level_is_removed(client):
    response = client.put("/preferences", json={"career_levels": ["internship", "junior"]})
    assert response.status_code == 200
    assert response.json()["career_levels"] == ["junior"]


@pytest.mark.parametrize(
    "title,expected",
    [
        ("AI & Technology Consultant", "AI Consultant"),
        ("Senior Data Analytics Consultant", "Data Consultant"),
        ("Digital Transformation Consultant", "Technology Consultant"),
        ("Machine Learning Advisor", "AI Consultant"),
        ("Recruitment Consultant", None),
    ],
)
def test_consulting_families(title, expected):
    assert family(title) == expected


@pytest.mark.parametrize(
    "requirement",
    [
        "Advanced Python expertise",
        "Production experience with Python",
        "Strong proficiency in Python",
        "Python or Java experience",
    ],
)
def test_skill_mentions_do_not_prove_qualified_requirements(requirement):
    raw = "Skills: Python, Java"
    row = SimpleNamespace(id="e", **extract_cv(raw)[0][0])
    req = SimpleNamespace(
        id="r", skill="Python", min_years=None, category="skill", text=requirement, required=True
    )
    assert match_requirement(req, [row], raw)["status"] == "not_verified"


@pytest.mark.parametrize("raw", ["I plan to learn Python", "I do not know Python"])
def test_old_evidence_skill_tags_cannot_override_negative_text(raw):
    row = SimpleNamespace(id="e", quote=raw, start=0, end=len(raw), section="skills", skills=["Python"])
    req = SimpleNamespace(
        id="r", skill="Python", min_years=None, category="skill", text="Python", required=True
    )
    assert match_requirement(req, [row], raw)["status"] == "not_verified"


def test_alternative_skills_remain_one_requirement():
    rows = extract_requirements("Requirements\nExperience with Python or Java.")
    assert len(rows) == 1
    assert rows[0]["skill"] is None


def test_all_role_preferences_are_accepted(client):
    from rolefit.normalization import FAMILIES

    assert client.put("/preferences", json={"families": FAMILIES}).status_code == 200
