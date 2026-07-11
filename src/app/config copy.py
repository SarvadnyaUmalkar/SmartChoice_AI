"""
SmartChoice AI — Centralised Configuration
All environment-specific values are read from the .env file.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Always load from the SmartChoice_AI/ root, regardless of cwd
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# Absolute path to the project root (directory containing this file's parent)
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_INSTANCE_DIR = os.path.join(_BASE_DIR, "instance")
os.makedirs(_INSTANCE_DIR, exist_ok=True)


class Config:
    # ── Flask ─────────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "0") == "1"

    # ── Database ──────────────────────────────────────────────────────────────
    # Use absolute path so SQLite works regardless of cwd
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(_INSTANCE_DIR, 'smartchoice.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # ── Session ───────────────────────────────────────────────────────────────
    SESSION_COOKIE_SECURE: bool = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    PERMANENT_SESSION_LIFETIME: int = int(os.environ.get("PERMANENT_SESSION_LIFETIME", 86400))

    # ── IBM Watsonx.ai ────────────────────────────────────────────────────────
    # NO hardcoded us-south default. If IBM_WATSONX_URL is not in .env, we
    # use au-syd as the safe fallback for this project. The watsonx_client
    # module also reads directly from os.environ so it can never be stale.
    IBM_API_KEY: str      = os.environ.get("IBM_API_KEY", "")
    IBM_WATSONX_URL: str  = os.environ.get("IBM_WATSONX_URL", "https://au-syd.ml.cloud.ibm.com")
    IBM_PROJECT_ID: str   = os.environ.get("IBM_PROJECT_ID", "")
    GRANITE_MODEL_ID: str = os.environ.get("GRANITE_MODEL_ID", "ibm/granite-13b-instruct-v2")

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.environ.get("LOG_FILE", "logs/smartchoice.log")
    LOG_MAX_BYTES: int = int(os.environ.get("LOG_MAX_BYTES", 10_485_760))
    LOG_BACKUP_COUNT: int = int(os.environ.get("LOG_BACKUP_COUNT", 5))

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATELIMIT_DEFAULT: str = f"{os.environ.get('RATE_LIMIT', '60')} per minute"
    RATELIMIT_STORAGE_URL: str = "memory://"


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
