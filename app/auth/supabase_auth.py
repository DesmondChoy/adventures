"""Verify access tokens with the configured Supabase Auth service."""

import os
from uuid import UUID

import httpx

AUTH_TIMEOUT_SECONDS = 5.0


class InvalidAccessToken(Exception):
    """The supplied access token was rejected."""


class AuthenticationUnavailable(Exception):
    """Authentication could not be verified safely."""


async def verify_supabase_access_token(token: str) -> UUID:
    """Return Auth's user ID without trusting local JWT claims or signing secrets."""
    if (
        not token
        or not token.isascii()
        or any(character.isspace() for character in token)
    ):
        raise InvalidAccessToken

    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    publishable_key = os.getenv("SUPABASE_ANON_KEY")
    if not supabase_url or not publishable_key:
        raise AuthenticationUnavailable

    # The destination comes only from server configuration, never JWT claims.
    try:
        async with httpx.AsyncClient(
            timeout=AUTH_TIMEOUT_SECONDS, follow_redirects=False
        ) as client:
            response = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "apikey": publishable_key,
                    "Authorization": f"Bearer {token}",
                },
            )
    except (httpx.RequestError, httpx.InvalidURL):
        raise AuthenticationUnavailable from None

    if response.status_code in (401, 403):
        raise InvalidAccessToken
    if response.status_code != 200:
        raise AuthenticationUnavailable

    try:
        user = response.json()
        user_id = user.get("id") if isinstance(user, dict) else None
        if not isinstance(user_id, str):
            raise ValueError
        return UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        raise AuthenticationUnavailable from None
