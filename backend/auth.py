"""Auth helpers: manager JWT verify + candidate session-cookie verify."""
from __future__ import annotations

import jwt
from fastapi import HTTPException

from config import load_settings


def verify_manager_jwt(authorization_header: str | None) -> dict:
    """Verify a manager Supabase JWT and return its claims.

    Raises HTTPException(401) for missing/malformed/expired,
    HTTPException(403) for valid token with non-manager email.
    """
    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization_header.removeprefix("Bearer ").strip()
    settings = load_settings()
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    email = (claims.get("email") or "").lower()
    if email != settings.manager_email:
        raise HTTPException(status_code=403, detail="Not authorized as manager")
    return claims


def verify_candidate_session(candidate: dict, cookie_value: str | None) -> None:
    """Validate a candidate session cookie against the stored session_id.

    Raises HTTPException(410) if link_used is true,
    HTTPException(409) if cookie missing or mismatched.
    """
    if candidate.get("link_used"):
        raise HTTPException(status_code=410, detail="Link already used")
    expected = candidate.get("session_id")
    if not expected or cookie_value != expected:
        raise HTTPException(status_code=409, detail="Session in use elsewhere or expired")
