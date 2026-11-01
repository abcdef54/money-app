"""Application configuration.

Uses pydantic-settings so every value can be overridden with an environment
variable (or a `.env` file). Switching to PostgreSQL later only requires
setting DATABASE_URL, e.g.:

    DATABASE_URL=postgresql+psycopg://user:pass@localhost/finance
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Personal Finance Analytics"
    database_url: str = f"sqlite:///{BASE_DIR / 'finance.db'}"
    default_currency: str = "VND"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    attachments_dir: Path = BASE_DIR / "attachments"


settings = Settings()
