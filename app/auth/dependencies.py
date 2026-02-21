import os
import logging
from typing import Optional
from uuid import UUID

import jwt  # PyJWT
from fastapi import Depends, Request

# Configure logger
logger = logging.getLogger(__name__)


def get_supabase_jwt_secret_from_env() -> Optional[str]:
    """Retrieves the Supabase JWT secret from environment variables."""
    return os.getenv("SUPABASE_JWT_SECRET")


def _extract_bearer_token(request: Request) -> Optional[str]:
    """Extract a bearer token from the Authorization header."""
    authorization = request.headers.get("authorization")
    if not authorization:
        return None

    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer":
        return None

    token = token.strip()
    return token if token else None


async def get_current_user_id_optional(
    request: Request,
    supabase_jwt_secret: str = Depends(get_supabase_jwt_secret_from_env),
) -> Optional[UUID]:
    """
    FastAPI dependency to verify an optional JWT and extract the user ID.
    Extracts JWT token from Authorization header in format "Bearer <token>".

    If a token is provided, it's verified using the SUPABASE_JWT_SECRET.
    - If valid, the user_id (from 'sub' claim) is returned as a UUID.
    - If invalid (e.g., expired, signature error), a warning is logged, and None is returned.
    - If no token is provided, None is returned.
    """
    logger.debug(
        "Processing optional JWT authentication",
        extra={"path": request.url.path, "method": request.method},
    )

    token = _extract_bearer_token(request)
    if not token:
        return None

    if not supabase_jwt_secret:
        logger.error("SUPABASE_JWT_SECRET is not set. Cannot verify JWT.")
        return None

    try:
        # Supabase typically uses HS256 for its JWTs signed with the JWT secret
        # Supabase tokens have audience "authenticated" for logged-in users
        # Add 60-second leeway to handle clock skew between client/server (industry standard)
        decoded_token = jwt.decode(
            token,
            supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",  # Supabase uses "authenticated" as audience
            leeway=60,  # 60-second tolerance for clock skew (industry standard)
        )

        user_id_str = decoded_token.get("sub")
        if user_id_str:
            try:
                user_uuid = UUID(user_id_str)
                return user_uuid
            except ValueError:
                logger.warning("JWT contained a non-UUID 'sub' claim")
                return None
        else:
            logger.warning("JWT token is valid but missing a 'sub' claim")
            return None
    except jwt.ExpiredSignatureError:
        logger.info("JWT token has expired")
        return None
    except jwt.InvalidAudienceError:
        logger.warning("JWT token has invalid audience")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT token")
        return None
    except Exception as e:
        logger.error("Unexpected error during JWT decoding: %s", type(e).__name__)
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
