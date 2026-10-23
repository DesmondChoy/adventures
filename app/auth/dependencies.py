import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request

from app.auth.supabase_auth import (
    AuthenticationUnavailable,
    InvalidAccessToken,
    verify_supabase_access_token,
)

logger = logging.getLogger(__name__)


def _extract_bearer_token(request: Request) -> Optional[str]:
    """Allow a missing header for guests; reject malformed supplied credentials."""
    authorization = request.headers.get("authorization")
    if authorization is None:
        return None

    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise InvalidAccessToken
    return token.strip()


async def get_current_user_id_optional(request: Request) -> Optional[UUID]:
    """Return a verified user ID, or None only when no credentials were supplied."""
    try:
        token = _extract_bearer_token(request)
        if token is None:
            return None
        return await verify_supabase_access_token(token)
    except InvalidAccessToken:
        logger.info("Supplied authentication was rejected")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated or token is invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except AuthenticationUnavailable:
        logger.warning("Supabase authentication is unavailable")
        raise HTTPException(
            status_code=503, detail="Authentication service is unavailable."
        ) from None


async def get_current_user_id(
    user_id: Optional[UUID] = Depends(get_current_user_id_optional),
) -> UUID:
    """Require a verified Supabase user."""
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated or token is invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
