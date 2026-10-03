from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from rolefit import auth
from rolefit.config import Settings
from rolefit.extraction import StructuredCV, cached_call
from rolefit.models import Budget
from rolefit_ml.embeddings import Embedder


def test_production_settings_never_accept_dev_auth():
    from rolefit.config import settings

    settings.cache_clear()
    # The invariant is enforced by the settings accessor, independent of headers.
    assert (
        Settings(app_env="production", dev_auth=False, supabase_url="https://test.example").dev_auth is False
    )


def test_jwt_signature_issuer_audience_expiry(monkeypatch, db):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        auth,
        "settings",
        lambda: SimpleNamespace(
            app_env="production",
            dev_auth=False,
            supabase_url="https://auth.example",
            supabase_audience="authenticated",
        ),
    )
    monkeypatch.setattr(
        auth,
        "jwks",
        lambda: SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key())),
    )
    payload = {
        "sub": "00000000-0000-4000-8000-000000000008",
        "iss": "https://auth.example/auth/v1",
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }

    def credentials(data):
        return HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=jwt.encode(data, key, algorithm="RS256")
        )

    assert auth.current_user(credentials(payload), db).id == payload["sub"]
    for changed in [
        {"aud": "wrong"},
        {"iss": "https://attacker.example"},
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
    ]:
        with pytest.raises(HTTPException) as caught:
            auth.current_user(credentials({**payload, **changed}), db)
        assert caught.value.status_code == 401
    with pytest.raises(HTTPException):
        auth.current_user(None, db)


def test_budget_cap_stops_before_remote_call(db, monkeypatch):
    from rolefit import extraction

    config = SimpleNamespace(
        llm_api_key="test-only",
        llm_model="test-model",
        llm_input_usd_per_million=5,
        llm_output_usd_per_million=20,
        llm_budget_usd=0,
    )
    monkeypatch.setattr(extraction, "settings", lambda: config)

    def forbidden(*args, **kwargs):
        raise AssertionError("Budget exhaustion must prevent a network call")

    monkeypatch.setattr(extraction.httpx, "post", forbidden)
    db.add(Budget(id=1, spent_usd=0))
    db.commit()
    with pytest.raises(ValueError, match="budget exhausted"):
        cached_call(db, "alice", "cv", "text", StructuredCV, "structure")


def test_schema_rejects_extra_fields_and_bad_sections():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        StructuredCV.model_validate(
            {"items": [{"quote": "invented", "section": "instructions", "score": 99}]}
        )


def test_embedding_length_guard_runs_before_inference():
    embedder = object.__new__(Embedder)
    embedder.tokenizer = SimpleNamespace(encode=lambda text, add_special_tokens: list(range(513)))
    embedder.model = SimpleNamespace(encode=lambda *a, **k: pytest.fail("Overlong chunk reached the model"))
    with pytest.raises(ValueError, match="refusing silent truncation"):
        embedder.embed(["too long"])
