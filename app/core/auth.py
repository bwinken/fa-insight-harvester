"""JWT authentication via oauth2-proxy.

oauth2-proxy handles the full OAuth 2.0 flow (login, callback, token exchange).
Nginx injects the access token as an Authorization header via auth_request.
This module only verifies the JWT and extracts user info.
"""

import time
from pathlib import Path

import jwt
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.fa_case import FAUser

_public_key: str | None = None
_public_key_loaded_at: float = 0.0
_PUBLIC_KEY_TTL: float = 3600.0  # re-read from disk every hour


def _get_public_key() -> str:
    global _public_key, _public_key_loaded_at
    now = time.monotonic()
    if _public_key is None or (now - _public_key_loaded_at) > _PUBLIC_KEY_TTL:
        key_path = Path(settings.auth_public_key_path)
        if not key_path.exists():
            raise RuntimeError(f"Auth public key not found: {key_path}")
        _public_key = key_path.read_text()
        _public_key_loaded_at = now
    return _public_key


def verify_token(token: str) -> dict:
    """Verify JWT token using Auth Center's RS256 public key."""
    try:
        payload = jwt.decode(
            token,
            _get_public_key(),
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


def get_current_user_payload(request: Request) -> dict:
    """Extract and verify user from JWT.

    Token sources (in priority order):
    1. Authorization header (injected by Nginx from oauth2-proxy)
    2. Dev mode fallback (DEV_SKIP_AUTH=true)
    """
    if settings.dev_skip_auth:
        import os

        if os.environ.get("ENVIRONMENT") == "production":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Security configuration error: DEV_SKIP_AUTH in production",
            )
        return {"sub": "dev", "org_id": "dev", "scopes": ["read", "write", "admin"]}

    # oauth2-proxy → Nginx → Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return verify_token(token)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def require_scope(request: Request, scope: str) -> dict:
    """Verify JWT and check that the token includes the required scope.

    Raises 403 if the user is authenticated but lacks the scope.
    """
    payload = get_current_user_payload(request)
    scopes = payload.get("scopes", [])
    if scope not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient scope: '{scope}' required",
        )
    return payload


async def get_or_create_user(db: AsyncSession, payload: dict) -> FAUser:
    """Get or create FAUser from JWT payload."""
    employee_name = payload["sub"]
    org_id = payload.get("org_id")

    result = await db.execute(
        select(FAUser).where(FAUser.employee_name == employee_name)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = FAUser(employee_name=employee_name, org_id=org_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif user.org_id != org_id:
        user.org_id = org_id
        await db.commit()

    return user
