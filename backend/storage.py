"""Helpers for Supabase Storage signed URLs."""
from __future__ import annotations

from config import load_settings
from supabase_client import get_supabase


def bucket_for_pool(pool: str) -> str:
    s = load_settings()
    return {
        "tiktok": s.bucket_tiktoks,
        "nano_banana": s.bucket_nano_banana,
        "kling": s.bucket_kling,
    }[pool]


def signed_url_for_item(pool: str, storage_path: str) -> str:
    """Return a short-lived signed URL for the given item."""
    s = load_settings()
    bucket = bucket_for_pool(pool)
    res = get_supabase().storage.from_(bucket).create_signed_url(
        storage_path, s.signed_url_ttl_seconds
    )
    # supabase-py returns {'signedURL': '...'} or {'signed_url': '...'} depending on version
    return res.get("signedURL") or res.get("signed_url") or ""
