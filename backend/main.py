import os
import sys
import config

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import socket

from routers import voice, sensors, app

# Create FastAPI app
fastapi_app = FastAPI(
    title="Smart Home Backend API",
    description="Backend API for ESP32 Smart Home with Voice Assistant",
    version="1.0.0",
    docs_url="/docs" if not config.IS_PRODUCTION else None,
    redoc_url="/redoc" if not config.IS_PRODUCTION else None,
)

# CORS Configuration
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
fastapi_app.include_router(voice.router, tags=["Voice Assistant"])
fastapi_app.include_router(sensors.router, tags=["Sensors & Relays"])
fastapi_app.include_router(app.router, tags=["App API"])

# Root endpoint
@fastapi_app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Smart Home Backend API",
        "version": "1.0.0",
        "environment": config.ENVIRONMENT,
        "endpoints": {
            "health": "/health",
            "sensors": "/api/sensor/data",
            "relay_control": "/api/device/control",
            "voice_ws": "/ws/voice",
            "relay_ws": "/ws/relay"
        }
    }

@fastapi_app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("[STARTUP] Smart Home Backend API Starting...")
    print("=" * 60)
    print(f"[CONFIG] Environment: {config.ENVIRONMENT}")
    print(f"[CONFIG] Gemini API Key: {'✓ Set' if config.GEMINI_API_KEY else '✗ Missing'}")
    print(f"[CONFIG] ESP32 URL: {config.ESP32_SENSOR_URL}")
    
    # Check available Gemini models
    if config.GEMINI_API_KEY:
        from services import gemini_service
        try:
            available_models = gemini_service.list_available_models()
            if available_models:
                print(f"[CONFIG] Gemini Models: {len(available_models)} available")
            else:
                print("[WARNING] No Gemini models available - check API key and quota")
        except Exception as e:
            print(f"[WARNING] Failed to check Gemini models: {e}")
    
    # Get server IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"
    
    print(f"[NETWORK] Local IP: {ip}")
    print(f"[NETWORK] Port: {config.PORT}")
    print("=" * 60)
    print("[STARTUP] Backend ready!")
    print("=" * 60)

@fastapi_app.on_event("shutdown")
async def shutdown_event():
    print("[SHUTDOWN] Backend shutting down...")

# Global exception handler
@fastapi_app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"[ERROR] Unhandled exception: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:fastapi_app",
        host=config.HOST,
        port=config.PORT,
        reload=not config.IS_PRODUCTION,
        log_level="info"
    )
