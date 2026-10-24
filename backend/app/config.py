"""Runtime configuration read from environment variables.

Real environment variables only: `.env` files are not loaded automatically (that would
need an extra dependency). The defaults below work for local development without any file.
"""

import os
from dataclasses import dataclass

DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
# Field limits already bound the payload size in practice; this is a second safety net.
MAX_REQUEST_BYTES = 256 * 1024


@dataclass(frozen=True)
class Settings:
    cors_allow_origins: tuple[str, ...]
    max_request_bytes: int = MAX_REQUEST_BYTES


def load_settings() -> Settings:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", DEFAULT_CORS_ORIGINS)
    origins = tuple(origin.strip() for origin in raw.split(",") if origin.strip())
    return Settings(cors_allow_origins=origins)
