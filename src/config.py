"""Configuration management for CustomerVoice AI."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Application settings loaded from environment variables."""

    APP_NAME: str = os.getenv("APP_NAME", "CustomerVoice AI")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/customervoice_db",
    )


settings = Settings()
