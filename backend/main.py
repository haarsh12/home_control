import os
import config

os.environ["PATH"] += os.pathsep + config.FFMPEG_PATH

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import socket

from routers import voice, sensors, app

fastapi_app = FastAPI()

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(voice.router)
fastapi_app.include_router(sensors.router)
fastapi_app.include_router(app.router)

@fastapi_app.on_event("startup")
async def startup_event():
    print("[STARTUP] Starting FastAPI backend...")
    print(f"[STARTUP] FFMPEG Path added: {config.FFMPEG_PATH}")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"
    print(f"[STARTUP] Backend IP: {ip}")

if __name__ == "__main__":
    uvicorn.run("main:fastapi_app", host="0.0.0.0", port=8000, reload=True)
