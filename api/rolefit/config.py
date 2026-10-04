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
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_budget_usd: float = 5.0
    llm_input_usd_per_million: float = 5.0
    llm_output_usd_per_million: float = 20.0


@lru_cache
def settings() -> Settings:
    value = Settings()
    if value.app_env != "development" and value.dev_auth:
        raise ValueError("DEV_AUTH must be false outside development")
    if value.app_env != "development" and not value.supabase_url:
        raise ValueError("SUPABASE_URL is required outside development")
    return value
