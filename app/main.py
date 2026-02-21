from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.routers import web, websocket_router, summary_router, feedback_router
from app.utils.logging_config import setup_logging
from app.middleware import get_middleware_stack
from app.services.state_storage_service import StateStorageService
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import asyncio
import os

# Load environment variables
load_dotenv()

# Setup structured logging
logger = setup_logging()

# Rate limiter
from app.rate_limit import limiter


async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )

# Initialize state storage service (singleton – subsequent StateStorageService()
# calls in routers/dependencies will return this same instance)
state_storage_service = StateStorageService()


async def periodic_cleanup():
    """Run cleanup of expired states periodically."""
    while True:
        try:
            await state_storage_service.cleanup_expired_adventures()
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")

        # Run every 30 minutes
        await asyncio.sleep(30 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if not os.getenv("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "The application cannot start without it. "
            "Please set SECRET_KEY in your .env file."
        )
    logger.info("Application starting up")

    # Start background task for cleaning up expired states
    cleanup_task = asyncio.create_task(periodic_cleanup())
    logger.info("Started background task for cleaning up expired states")

    yield

    # Shutdown
    logger.info("Application shutting down")

    # Cancel the cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("Cleanup task cancelled")


# Initialize FastAPI with middleware stack
app = FastAPI(
    title="Learning Odyssey",
    lifespan=lifespan,
    middleware=get_middleware_stack(),
)

# Set up rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# Mount React app assets
app.mount(
    "/adventure/assets",
    StaticFiles(directory="app/static/summary-chapter/assets"),
    name="react_assets",
)


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico")


app.include_router(web.router)
app.include_router(websocket_router.router)
app.include_router(summary_router.router, prefix="/adventure")
app.include_router(feedback_router.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
