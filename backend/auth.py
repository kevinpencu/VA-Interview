"""Auth helpers: manager JWT verify + candidate session-cookie verify."""
from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

from config import load_settings


# Supabase issues JWTs in one of two flavors:
#   - Legacy projects: HS256 signed with the project JWT secret
#   - Modern projects: ES256/RS256/EdDSA signed asymmetrically, public keys at /auth/v1/.well-known/jwks.json
# We support both so the same code runs against any project.
_ASYMMETRIC_ALGS = {"ES256", "RS256", "EdDSA"}


@lru_cache(maxsize=1)
def _jwks_client(supabase_url: str) -> PyJWKClient:
    return PyJWKClient(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")


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
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    alg = header.get("alg", "HS256")
    try:
        if alg == "HS256":
            claims = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        elif alg in _ASYMMETRIC_ALGS:
            signing_key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
            )
        else:
            raise HTTPException(status_code=401, detail=f"Unsupported alg: {alg}")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    email = (claims.get("email") or "").lower()
    if email not in settings.manager_emails:
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
