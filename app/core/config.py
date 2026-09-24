from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ai_infrastructure_copilot"
    postgres_user: str = "ai_copilot_app"
    postgres_password: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
