from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers import web, websocket
from app.utils.logging_config import setup_logging
import os
import uuid
import logging
from contextlib import asynccontextmanager
from datetime import datetime

# Setup structured logging
logger = setup_logging()


# Custom middleware classes
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


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.utcnow()
        session = request.session
        request_id = session.get("request_id", "no_request_id")

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
                    "status_code": getattr(response, "status_code", 500),
                    "duration_ms": duration_ms,
                },
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up")
    yield
    # Shutdown
    logger.info("Application shutting down")


# Define middleware stack
middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY", "your-secret-key-here"),
        session_cookie="story_app_session",
        max_age=86400,  # 24 hours
        same_site="lax",  # Improved security
        https_only=bool(os.getenv("HTTPS_ONLY", False)),  # Enable in production
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

# Initialize FastAPI with middleware stack
app = FastAPI(
    title="Educational Story App",
    lifespan=lifespan,
    middleware=middleware,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico")


app.include_router(web.router)
app.include_router(websocket.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
