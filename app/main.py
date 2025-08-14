from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import web, websocket_router, summary_router
from app.utils.logging_config import setup_logging
from app.middleware import get_middleware_stack
from app.services.state_storage_service import StateStorageService
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import asyncio

# Load environment variables
load_dotenv()

# Setup structured logging
logger = setup_logging()

# Initialize state storage service
state_storage_service = StateStorageService()

# Export the state storage service instance for use in other modules
from app.services.state_storage_service import (
    StateStorageService as _StateStorageService,
)

_StateStorageService._instance = state_storage_service


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


# Direct test route with the same path as the summary router
@app.get("/adventure/direct-summary")
async def direct_summary():
    """Direct test route with the same path as the summary router."""
    return FileResponse("app/static/test_summary.html")


# Simple test route that returns plain text
@app.get("/test-text")
async def test_text():
    """Simple test route that returns plain text."""
    return "This is a test route that returns plain text"


# Simple test route in the adventure path that returns plain text
@app.get("/adventure/test-text")
async def adventure_test_text():
    """Simple test route in the adventure path that returns plain text."""
    return "This is a test route in the adventure path that returns plain text"


app.include_router(web.router)
app.include_router(websocket_router.router)
app.include_router(summary_router.router, prefix="/adventure")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
