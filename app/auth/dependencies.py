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
    logger.info("[JWT DEBUG] get_current_user_id_optional function called!")
    logger.info(f"[JWT DEBUG] Request method: {request.method}")
    logger.info(f"[JWT DEBUG] Request URL: {request.url}")
    logger.info(f"[JWT DEBUG] Request headers: {dict(request.headers)}")

    # Extract token from Authorization header
    authorization = request.headers.get("authorization")
    logger.info(f"[JWT DEBUG] Authorization header: {authorization}")

    if not authorization:
        logger.info("[JWT DEBUG] No Authorization header provided - returning None")
        return None

    # Parse "Bearer <token>" format
    if not authorization.startswith("Bearer "):
        logger.warning(
            "[JWT DEBUG] Authorization header doesn't start with 'Bearer ' - returning None"
        )
        return None

    token = authorization[7:]  # Remove "Bearer " prefix
    logger.info(f"[JWT DEBUG] Extracted token (first 20 chars): {token[:20]}...")
    logger.info(f"[JWT DEBUG] Token length: {len(token)}")

    if not supabase_jwt_secret:
        logger.error("[JWT DEBUG] SUPABASE_JWT_SECRET is not set. Cannot verify JWT.")
        return None

    logger.info(f"[JWT DEBUG] JWT secret available: {bool(supabase_jwt_secret)}")
    logger.info(
        f"[JWT DEBUG] JWT secret length: {len(supabase_jwt_secret) if supabase_jwt_secret else 0}"
    )

    try:
        # Supabase typically uses HS256 for its JWTs signed with the JWT secret
        # Supabase tokens have audience "authenticated" for logged-in users
        # Add 60-second leeway to handle clock skew between client/server (industry standard)
        logger.info(
            "[JWT DEBUG] Attempting to decode JWT with secret and 60s clock skew tolerance..."
        )
        decoded_token = jwt.decode(
            token,
            supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",  # Supabase uses "authenticated" as audience
            leeway=60,  # 60-second tolerance for clock skew (industry standard)
        )
        logger.info(
            f"[JWT DEBUG] Successfully decoded JWT payload keys: {list(decoded_token.keys())}"
        )
        logger.info(f"[JWT DEBUG] JWT 'sub' claim: {decoded_token.get('sub')}")
        logger.info(f"[JWT DEBUG] JWT 'aud' claim: {decoded_token.get('aud')}")
        logger.info(f"[JWT DEBUG] JWT 'exp' claim: {decoded_token.get('exp')}")
        logger.info(f"[JWT DEBUG] JWT 'iat' claim: {decoded_token.get('iat')}")
        logger.info(f"[JWT DEBUG] JWT 'iss' claim: {decoded_token.get('iss')}")

        user_id_str = decoded_token.get("sub")
        if user_id_str:
            try:
                user_uuid = UUID(user_id_str)
                logger.info(
                    f"[JWT DEBUG] Successfully extracted and converted user_id: {user_uuid}"
                )
                return user_uuid
            except ValueError as uuid_error:
                logger.error(
                    f"[JWT DEBUG] Failed to convert user_id to UUID: {uuid_error}"
                )
                return None
        else:
            logger.warning(
                "[JWT DEBUG] JWT token is valid but missing 'sub' (user_id) claim."
            )
            return None
    except jwt.ExpiredSignatureError:
        logger.warning("[JWT DEBUG] JWT token has expired.")
        return None
    except jwt.InvalidAudienceError as e:
        logger.warning(f"[JWT DEBUG] JWT token has invalid audience: {e}")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"[JWT DEBUG] Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(
            f"[JWT DEBUG] An unexpected error occurred during JWT decoding: {e}"
        )
        logger.error(f"[JWT DEBUG] Exception type: {type(e).__name__}")
        logger.error(f"[JWT DEBUG] Exception args: {e.args}")
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
