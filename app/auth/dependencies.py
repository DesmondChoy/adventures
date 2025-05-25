import os
import logging
from typing import Optional
from uuid import UUID

import jwt  # PyJWT
from fastapi import Depends, Query

# Configure logger
logger = logging.getLogger(__name__)


def get_supabase_jwt_secret_from_env() -> Optional[str]:
    """Retrieves the Supabase JWT secret from environment variables."""
    return os.getenv("SUPABASE_JWT_SECRET")


async def get_current_user_id_optional(
    token: Optional[str] = Query(None, description="JWT token for authentication"),
    supabase_jwt_secret: str = Depends(get_supabase_jwt_secret_from_env),
) -> Optional[UUID]:
    """
    FastAPI dependency to verify an optional JWT and extract the user ID.

    If a token is provided, it's verified using the SUPABASE_JWT_SECRET.
    - If valid, the user_id (from 'sub' claim) is returned as a UUID.
    - If invalid (e.g., expired, signature error), a warning is logged, and None is returned.
    - If no token is provided, None is returned.
    """
    if not token:
        logger.debug("No JWT token provided.")
        return None

    if not supabase_jwt_secret:
        logger.error("SUPABASE_JWT_SECRET is not set. Cannot verify JWT.")
        # Depending on security policy, you might raise an error here
        # or simply deny access by returning None.
        return None

    try:
        # Supabase typically uses HS256 for its JWTs signed with the JWT secret
        decoded_token = jwt.decode(token, supabase_jwt_secret, algorithms=["HS256"])
        user_id_str = decoded_token.get("sub")
        if user_id_str:
            logger.debug(f"Successfully decoded JWT for user_id: {user_id_str}")
            return UUID(user_id_str)
        else:
            logger.warning("JWT token is valid but missing 'sub' (user_id) claim.")
            return None
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired.")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during JWT decoding: {e}")
        return None


async def get_current_user_id(
    user_id: Optional[UUID] = Depends(get_current_user_id_optional),
) -> UUID:
    """
    FastAPI dependency that requires a valid JWT and returns the user ID.
    If the token is missing, invalid, or the user_id cannot be extracted,
    it raises an HTTPException.
    """
    if user_id is None:
        from fastapi import (
            HTTPException,
        )  # Local import to avoid circular dependency if this file grows

        logger.warning(
            "User authentication required, but token was invalid or missing."
        )
        raise HTTPException(
            status_code=401,
            detail="Not authenticated or token is invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
