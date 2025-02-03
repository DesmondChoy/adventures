from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import web, websocket
import os

app = FastAPI(title="Educational Story App")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico")


app.include_router(web.router)
app.include_router(websocket.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
