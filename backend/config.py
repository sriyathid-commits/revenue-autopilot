from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass  # Read-only filesystem (e.g. Render) — database.py uses DATABASE_URL env var directly


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # On Render, DATABASE_URL is set via env var to sqlite:////app/data/...
    # Locally it defaults to ./data/revenue_autopilot.db
    database_url: str = f"sqlite:///{(DATA_DIR / 'revenue_autopilot.db').as_posix()}"
    app_env: str = "local"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    high_value_threshold: float = 50_000.0
    high_risk_threshold: float = 0.75
    low_confidence_threshold: float = 0.55

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
