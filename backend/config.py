"""Environment-derived settings + scoring thresholds."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str | None = None, *, required: bool = False) -> str:
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val or ""


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_service_key: str
    supabase_jwt_secret: str
    # Tuple of lowercase emails allowed to log in as a manager.
    # Parsed from MANAGER_EMAIL (comma-separated list).
    manager_emails: tuple[str, ...]
    bucket_tiktoks: str
    bucket_nano_banana: str
    bucket_kling: str
    bucket_tutorial: str
    signed_url_ttl_seconds: int
    session_cookie_max_age_seconds: int
    cors_origins: tuple[str, ...]
    cookie_secure: bool

    @property
    def manager_email(self) -> str:
        """Back-compat: first listed manager. Useful for one-off setup scripts."""
        return self.manager_emails[0] if self.manager_emails else ""


def _parse_emails(raw: str) -> tuple[str, ...]:
    return tuple(e.strip().lower() for e in raw.split(",") if e.strip())


def load_settings() -> Settings:
    return Settings(
        supabase_url=_env("SUPABASE_URL", required=True),
        supabase_service_key=_env("SUPABASE_SERVICE_KEY", required=True),
        supabase_jwt_secret=_env("SUPABASE_JWT_SECRET", required=True),
        manager_emails=_parse_emails(_env("MANAGER_EMAIL", required=True)),
        bucket_tiktoks=_env("BUCKET_TIKTOKS", "tiktoks"),
        bucket_nano_banana=_env("BUCKET_NANO_BANANA", "nano_banana"),
        bucket_kling=_env("BUCKET_KLING", "kling"),
        bucket_tutorial=_env("BUCKET_TUTORIAL", "tutorial"),
        signed_url_ttl_seconds=int(_env("SIGNED_URL_TTL_SECONDS", "60")),
        session_cookie_max_age_seconds=int(_env("SESSION_COOKIE_MAX_AGE_SECONDS", "14400")),
        cors_origins=tuple(s.strip() for s in _env("CORS_ORIGINS", "http://localhost:5173").split(",") if s.strip()),
        cookie_secure=_env("COOKIE_SECURE", "false").lower() in ("true", "1", "yes"),
    )


# ============================================================
# Test composition + scoring constants (LOCKED — do not change without spec update)
# ============================================================
ITEMS_PER_STEP = 30
FORCED_JUSTIFICATIONS_PER_STEP = 2

POOLS = ("tiktok", "nano_banana", "kling")

QUIZ_QUESTION_COUNT = 5
QUIZ_PASS_THRESHOLD = 4    # ≥4/5 to proceed

# Auto-fail thresholds
STEP_ACCURACY_FAIL_FLOOR = 0.70
# Auto-borderline thresholds
STEP_ACCURACY_BORDERLINE_FLOOR = 0.80
TAB_SWITCH_BORDERLINE_THRESHOLD = 5
