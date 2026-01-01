from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Adds Cache-Control headers for static assets to improve repeat load times.

    - Applies caching to paths under `/static/` except for `.html` files.
    - Uses 1-day cache to balance performance with update freshness.
    - Does NOT use 'immutable' to allow browsers to revalidate on updates.
    """

    def __init__(self, app, max_age: int = 86400):  # 1 day (allows revalidation)
        super().__init__(app)
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        path = request.url.path
        if path.startswith("/static/") and not path.endswith(".html"):
            # Use version query strings for cache busting (e.g., ?v=20260101b)
            # Without 'immutable', browsers will check for updates after max_age expires
            response.headers.setdefault(
                "Cache-Control",
                f"public, max-age={self.max_age}",
            )
        return response

