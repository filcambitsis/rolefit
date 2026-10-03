import pytest
from fastapi import Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from rolefit.auth import current_user
from rolefit.db import Base, get_db
from rolefit.main import app
from rolefit.models import Job, User
from rolefit.normalization import content_hash


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    db.add_all([User(id="alice", preferences={}), User(id="bob", preferences={})])
    db.commit()

    def override_user(x_test_user: str = Header("alice")):
        return db.get(User, x_test_user)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[current_user] = override_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def job(db):
    description = "Requirements\nExperience with Python and SQL.\nPreferred\nExperience with Kubernetes."
    job = Job(
        provider="greenhouse",
        board="test",
        external_id="1",
        company="Test Company",
        title="AI Engineer",
        url="https://example.com/job",
        description=description,
        content_hash=content_hash(description),
        location="Amsterdam",
        countries=["NL"],
        family="AI Engineer",
        language="en",
        employment="full-time",
        employment_provenance="inferred",
        workplace="hybrid",
        workplace_provenance="structured",
    )
    db.add(job)
    db.commit()
    return job
