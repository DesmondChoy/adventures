from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import web, websocket
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


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico")


app.include_router(web.router)
app.include_router(websocket.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
