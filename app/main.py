from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import web, websocket_router, summary_router
from app.utils.logging_config import setup_logging
from app.middleware import get_middleware_stack
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Setup structured logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up")
    yield
    # Shutdown
    logger.info("Application shutting down")


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


# Direct test routes to diagnose routing issues
@app.get("/test-summary")
async def test_summary():
    """Test route to diagnose routing issues."""
    return FileResponse("app/static/test_summary.html")


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
