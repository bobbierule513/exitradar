"""Authentication and workspace tenancy helpers.

Never trust a client-supplied workspace_id. Membership is derived from the
authenticated JWT subject and workspace_members table.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Dict, Optional
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.api.app.core.config import get_settings
from apps.api.app.core.store import get_store

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


class AuthUser:
    """Authenticated user context."""

    def __init__(self, user_id: str, email: str = "", claims: Optional[Dict[str, Any]] = None):
        self.user_id = user_id
        self.email = email
        self.claims = claims or {}


def _decode_jwt(token: str) -> Dict[str, Any]:
    """Decode and validate a Supabase JWT."""
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        # Demo / local: accept opaque demo tokens
        if token.startswith("demo:"):
            parts = token.split(":", 2)
            return {"sub": parts[1] if len(parts) > 1 else "demo-user", "email": parts[2] if len(parts) > 2 else "demo@exitradar.local"}
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth not configured")

    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
    x_demo_user: Annotated[Optional[str], Header()] = None,
) -> AuthUser:
    """Resolve the current user from Bearer token or demo header."""
    settings = get_settings()

    if credentials and credentials.credentials:
        claims = _decode_jwt(credentials.credentials)
        return AuthUser(
            user_id=claims.get("sub", ""),
            email=claims.get("email", ""),
            claims=claims,
        )

    # Demo mode fallback for local development without Supabase Auth
    if settings.demo_mode or settings.environment == "development":
        user_id = x_demo_user or "00000000-0000-4000-8000-000000000001"
        return AuthUser(user_id=user_id, email="demo@exitradar.local")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def require_workspace_member(
    workspace_id: UUID,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> AuthUser:
    """Ensure the authenticated user is a member of the workspace."""
    from apps.api.app.core.tenancy import require_membership

    require_membership(store, str(workspace_id), user)
    return user
