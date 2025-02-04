from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from .request_id import RequestIDMiddleware
from .logging import LoggingMiddleware
import os


def get_middleware_stack():
    """
    Returns the configured middleware stack for the application.
    """
    return [
        Middleware(
            SessionMiddleware,
            secret_key=os.getenv("SECRET_KEY", "your-secret-key-here"),
            session_cookie="story_app_session",
            max_age=86400,  # 24 hours
            same_site="lax",  # Improved security
            https_only=bool(os.getenv("HTTPS_ONLY", False)),
        ),
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        Middleware(RequestIDMiddleware),
        Middleware(LoggingMiddleware),
    ]
