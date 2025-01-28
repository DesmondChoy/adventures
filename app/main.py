from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import web, websocket

# Initialize FastAPI app
app = FastAPI(title="Educational Story App")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(web.router)
app.include_router(websocket.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
