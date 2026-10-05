from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = f"sqlite:///{ROOT}/work/rolefit.db"
    app_env: str = "development"
    dev_auth: bool = False
    cors_origins: list[str] = ["http://localhost:3002", "http://127.0.0.1:3002"]
    supabase_url: str = ""
    supabase_audience: str = "authenticated"


@lru_cache
def settings() -> Settings:
    value = Settings()
    if value.app_env != "development" and value.dev_auth:
        raise ValueError("DEV_AUTH must be false outside development")
    if value.app_env != "development" and not value.supabase_url:
        raise ValueError("SUPABASE_URL is required outside development")
    return value
