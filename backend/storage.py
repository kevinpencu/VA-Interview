"""Helpers for Supabase Storage signed URLs."""
from __future__ import annotations

import logging
import time

from config import load_settings
from supabase_client import get_supabase

log = logging.getLogger("storage")


def bucket_for_pool(pool: str) -> str:
    s = load_settings()
    return {
        "tiktok": s.bucket_tiktoks,
        "nano_banana": s.bucket_nano_banana,
        "kling": s.bucket_kling,
    }[pool]


def signed_url_for_item(pool: str, storage_path: str) -> str:
    """Return a short-lived signed URL for the given item.

    Retries on transient Supabase Storage failures (network blip, rate limit
    burst) so a flaky storage call doesn't bubble up as a 500 to candidates."""
    s = load_settings()
    bucket = bucket_for_pool(pool)
    last_err: Exception | None = None
    for attempt in range(4):  # 4 total attempts: 0ms, 200ms, 600ms, 1400ms backoff
        try:
            res = get_supabase().storage.from_(bucket).create_signed_url(
                storage_path, s.signed_url_ttl_seconds
            )
            url = res.get("signedURL") or res.get("signed_url") or ""
            if not url:
                # Some supabase-py versions return an error dict instead of raising.
                raise RuntimeError(f"empty signed URL response: {res}")
            return url
        except Exception as e:
            last_err = e
            if attempt < 3:
                time.sleep(0.2 * (1 + attempt) ** 1.5)
                continue
            log.warning(
                "signed_url_for_item failed after %d attempts for %s/%s: %s",
                attempt + 1, bucket, storage_path, e,
            )
            raise
    raise last_err  # type: ignore[misc]  # unreachable
