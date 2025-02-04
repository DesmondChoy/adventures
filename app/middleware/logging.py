from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.utcnow()
        session = request.session
        request_id = session.get("request_id", "no_request_id")
        response = None

        # Log request start
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                "session_id": session.get("session_id", "no_session"),
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else "unknown",
            },
        )

        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "session_id": session.get("session_id", "no_session"),
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                },
            )
            raise
        finally:
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "session_id": session.get("session_id", "no_session"),
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": getattr(response, "status_code", 500)
                    if response
                    else 500,
                    "duration_ms": duration_ms,
                },
            )
