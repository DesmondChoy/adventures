import os
from typing import List

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from .cache_control import CacheControlMiddleware
from .logging import LoggingMiddleware
from .request_id import RequestIDMiddleware


def _parse_csv_env(var_name: str, default_values: List[str]) -> List[str]:
    """Parse comma-separated environment variables into a normalized list."""
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default_values

    parsed_values = [value.strip() for value in raw_value.split(",") if value.strip()]
    return parsed_values or default_values


def _parse_bool_env(var_name: str, default: bool) -> bool:
    """Parse boolean environment variable values safely."""
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def get_middleware_stack():
    """
    Returns the configured middleware stack for the application.
    """
    cors_allow_origins = _parse_csv_env(
        "CORS_ALLOW_ORIGINS",
        ["http://localhost:8000", "http://127.0.0.1:8000"],
    )
    cors_allow_credentials = _parse_bool_env("CORS_ALLOW_CREDENTIALS", True)

    if "*" in cors_allow_origins and cors_allow_credentials:
        cors_allow_credentials = False

    trusted_proxy_hosts = _parse_csv_env(
        "PROXY_TRUSTED_HOSTS",
        ["127.0.0.1", "localhost"],
    )
    allowed_hosts = _parse_csv_env(
        "ALLOWED_HOSTS",
        ["localhost", "127.0.0.1", "*.herokuapp.com"],
    )

    return [
        Middleware(ProxyHeadersMiddleware, trusted_hosts=trusted_proxy_hosts),
        Middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts),
        # Add aggressive caching for static assets to speed up repeat views
        Middleware(CacheControlMiddleware),
        Middleware(
            SessionMiddleware,
            secret_key=os.getenv("SECRET_KEY"),
            session_cookie="story_app_session",
            max_age=86400,  # 24 hours
            same_site="lax",  # Improved security
            https_only=_parse_bool_env("HTTPS_ONLY", False),
        ),
        Middleware(
            CORSMiddleware,
            allow_origins=cors_allow_origins,
            allow_credentials=cors_allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        Middleware(RequestIDMiddleware),
        Middleware(LoggingMiddleware),
    ]
