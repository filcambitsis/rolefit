from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

bearer = HTTPBearer(auto_error=False)
DEV_USER = "00000000-0000-4000-8000-000000000001"


@lru_cache
def jwks():
    return jwt.PyJWKClient(
        settings().supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json", cache_keys=True
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
):
    config = settings()
    if config.app_env == "development" and config.dev_auth and credentials is None:
        user_id = DEV_USER
    else:
        if credentials is None or not config.supabase_url:
            raise HTTPException(401, "Sign in to access your workspace")
        try:
            token = credentials.credentials
            key = jwks().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                key.key,
                algorithms=["RS256", "ES256"],
                audience=config.supabase_audience,
                issuer=config.supabase_url.rstrip("/") + "/auth/v1",
                options={"require": ["exp", "sub", "iss", "aud"]},
            )
            user_id = str(UUID(payload["sub"]))
        except (jwt.PyJWTError, ValueError):
            raise HTTPException(401, "Invalid or expired sign-in session") from None
    user = db.get(User, user_id)
    if not user:
        user = User(id=user_id, preferences={})
        db.add(user)
        db.commit()
    return user
