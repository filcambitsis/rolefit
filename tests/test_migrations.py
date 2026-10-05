"""Check both new installs and upgrades without touching a user's database."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OLD = "89519f2d867b"


def migrate(path, target="head"):
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", target],
        cwd=ROOT,
        env={**os.environ, "DATABASE_URL": f"sqlite:///{path}"},
        check=True,
        capture_output=True,
    )


def test_fresh_migrations(tmp_path):
    path = tmp_path / "fresh.db"
    migrate(path)
    with sqlite3.connect(path) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "extraction_cache" not in tables
        assert "llm_budget" not in tables
        assert {"cvs", "evidence", "jobs", "requirements", "decisions"} <= tables
        assert "embedding" not in {r[1] for r in db.execute("PRAGMA table_info(jobs)")}


def test_upgrade_preserves_saved_preferences_and_removes_retired_data(tmp_path):
    path = tmp_path / "existing.db"
    migrate(path, OLD)
    with sqlite3.connect(path) as db:
        prefs = json.dumps(
            {"families": ["AI Consultant", "AI Solutions & Implementation"], "employment": ["full-time"]}
        )
        db.execute(
            "INSERT INTO users (id,preferences,created_at) VALUES (?,?,?)", ("test", prefs, "2026-01-01")
        )
        db.execute("INSERT INTO llm_budget VALUES (1, 2.0)")
        db.execute("INSERT INTO extraction_cache VALUES ('cache','test','old','old','{}',1.0)")
        # Raw SQLite test connection leaves FK checks off; only decision cleanup is under test.
        db.execute("INSERT INTO decisions VALUES ('keep','test','job-a','saved')")
        db.execute("INSERT INTO decisions VALUES ('drop','test','job-b','skipped')")
        db.execute(
            "INSERT INTO cvs VALUES ('cv','test','Private test text','hash','test.txt','old','old',0,0,'2026-01-01')"
        )
    migrate(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT state FROM decisions").fetchall() == [("saved",)]
        preferences = json.loads(db.execute("SELECT preferences FROM users").fetchone()[0])
        assert preferences == {"families": ["AI Consulting & Solutions"], "employment": ["full-time"]}
        assert db.execute("SELECT text FROM cvs").fetchone()[0] == "Private test text"
