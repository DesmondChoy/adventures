from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import logging

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            if "request_id" not in request.session:
                request.session["request_id"] = str(uuid.uuid4())
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(
                "Error in RequestIDMiddleware",
                extra={
                    "error": str(e),
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            raise
