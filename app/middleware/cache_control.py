from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Adds Cache-Control headers for static assets to improve repeat load times.

    - Applies long-lived caching to paths under `/static/` except for `.html` files.
    - Leaves other responses unchanged.
    """

    def __init__(self, app, max_age: int = 31536000):  # 1 year
        super().__init__(app)
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        path = request.url.path
        if path.startswith("/static/") and not path.endswith(".html"):
            # Favor immutable caching for fingerprinted or rarely changing assets
            response.headers.setdefault(
                "Cache-Control",
                f"public, max-age={self.max_age}, immutable",
            )
        return response

