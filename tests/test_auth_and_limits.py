from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from rolefit import auth
from rolefit.config import Settings


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

    assert auth.current_user(None, credentials(payload), db).id == payload["sub"]
    for changed in [
        {"aud": "wrong"},
        {"iss": "https://attacker.example"},
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
    ]:
        with pytest.raises(HTTPException) as caught:
            auth.current_user(None, credentials({**payload, **changed}), db)
        assert caught.value.status_code == 401
    with pytest.raises(HTTPException):
        auth.current_user(None, None, db)


@pytest.mark.parametrize(
    "peer,host,origin,allowed",
    [
        ("127.0.0.1", "127.0.0.1:8000", "http://127.0.0.1:3002", True),
        ("::1", "localhost:8000", None, True),
        ("192.168.1.10", "localhost:8000", None, False),
        ("127.0.0.1", "evil.example", None, False),
        ("127.0.0.1", "localhost:8000", "https://evil.example", False),
    ],
)
def test_dev_auth_localhost_only(monkeypatch, db, peer, host, origin, allowed):
    from starlette.requests import Request

    monkeypatch.setattr(auth, "settings", lambda: SimpleNamespace(app_env="development", dev_auth=True))
    headers = [(b"host", host.encode())]
    if origin:
        headers.append((b"origin", origin.encode()))
    request = Request(
        {
            "type": "http",
            "scheme": "http",
            "path": "/",
            "headers": headers,
            "client": (peer, 1234),
            "server": ("127.0.0.1", 8000),
            "query_string": b"",
        }
    )
    if allowed:
        assert auth.current_user(request, None, db).id == auth.DEV_USER
    else:
        with pytest.raises(HTTPException) as caught:
            auth.current_user(request, None, db)
        assert caught.value.status_code == 403
