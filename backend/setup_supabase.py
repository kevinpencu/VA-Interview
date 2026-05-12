"""One-time bootstrap: create 4 storage buckets + manager auth user + manager_profiles row.

Idempotent: skips work that's already been done.
"""
from __future__ import annotations

import sys

from config import load_settings
from supabase_client import get_supabase


BUCKETS = [
    ("tiktoks", False),
    ("nano_banana", False),
    ("kling", False),
    ("tutorial", True),
]


def ensure_bucket(sb, name: str, public: bool) -> None:
    try:
        existing = sb.storage.list_buckets()
    except Exception as e:
        print(f"  [fail] could not list buckets: {e}")
        raise
    existing_names = {b.name if hasattr(b, "name") else b.get("name") for b in existing}
    if name in existing_names:
        print(f"  [skip] bucket '{name}' already exists")
        return
    try:
        sb.storage.create_bucket(name, options={"public": public})
        print(f"  [ok]   bucket '{name}' created ({'public' if public else 'private'})")
    except Exception as e:
        print(f"  [fail] create '{name}': {e}")
        raise


def ensure_manager_user(sb, email: str, password: str) -> str:
    """Return the auth user's UUID. Create if missing."""
    # Try create first
    try:
        res = sb.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
        })
        uid = res.user.id
        print(f"  [ok]   auth user '{email}' created (id={uid})")
        return uid
    except Exception as e:
        msg = str(e).lower()
        if "already" not in msg and "exist" not in msg and "registered" not in msg:
            print(f"  [fail] create user '{email}': {e}")
            raise
    # User exists — look it up
    page = 1
    while True:
        users = sb.auth.admin.list_users(page=page, per_page=200)
        items = users if isinstance(users, list) else getattr(users, "users", users)
        for u in items:
            u_email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
            if u_email and u_email.lower() == email.lower():
                uid = getattr(u, "id", None) or u["id"]
                print(f"  [skip] auth user '{email}' already exists (id={uid})")
                return uid
        if not items or len(items) < 200:
            break
        page += 1
    raise RuntimeError(f"Could not find user {email!r} after create-failed-as-exists")


def ensure_manager_profile(sb, uid: str, email: str) -> None:
    sb.table("manager_profiles").upsert({
        "id": uid,
        "email": email,
    }, on_conflict="id").execute()
    print(f"  [ok]   manager_profiles row upserted for {email}")


def main() -> int:
    settings = load_settings()
    sb = get_supabase()

    print("Creating storage buckets:")
    for name, public in BUCKETS:
        ensure_bucket(sb, name, public)

    print(f"\nProvisioning manager user '{settings.manager_email}':")
    if len(sys.argv) < 2:
        print("  usage: python setup_supabase.py <manager_password>", file=sys.stderr)
        return 2
    password = sys.argv[1]
    uid = ensure_manager_user(sb, settings.manager_email, password)

    print("\nLinking manager_profiles:")
    ensure_manager_profile(sb, uid, settings.manager_email)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
