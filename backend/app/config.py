"""Runtime configuration read from environment variables.

The backend loads local development secrets from backend/.env via python-dotenv.
The app still supports legacy AI_* environment names alongside the explicit Gemini
settings requested for this project.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env", override=False)

DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
MAX_REQUEST_BYTES = 256 * 1024
DEFAULT_AI_PROVIDER = "gemini"
DEFAULT_AI_MODEL = "gemini-3.8-flash"


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    cors_allow_origins: tuple[str, ...]
    max_request_bytes: int = MAX_REQUEST_BYTES
    ai_provider: str = DEFAULT_AI_PROVIDER
    ai_model: str = DEFAULT_AI_MODEL
    ai_api_key: str = ""
    ai_api_base_url: str = ""
    ai_parsing_enabled: bool = False


def load_settings() -> Settings:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", DEFAULT_CORS_ORIGINS)
    origins = tuple(origin.strip() for origin in raw.split(",") if origin.strip())
    ai_provider = (
        os.environ.get("AI_PROVIDER")
        or os.environ.get("GEMINI_PROVIDER")
        or DEFAULT_AI_PROVIDER
    ).strip() or DEFAULT_AI_PROVIDER
    ai_model = (
        os.environ.get("AI_MODEL")
        or os.environ.get("GEMINI_MODEL")
        or DEFAULT_AI_MODEL
    ).strip() or DEFAULT_AI_MODEL
    ai_api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("AI_API_KEY")
        or ""
    ).strip()
    ai_parsing_enabled = _truthy(os.environ.get("AI_PARSING_ENABLED")) or bool(ai_api_key)
    return Settings(
        cors_allow_origins=origins,
        ai_provider=ai_provider,
        ai_model=ai_model,
        ai_api_key=ai_api_key,
        ai_api_base_url=(os.environ.get("AI_API_BASE_URL") or "").strip(),
        ai_parsing_enabled=ai_parsing_enabled,
    )
