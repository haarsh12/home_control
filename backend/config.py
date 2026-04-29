import os
from pathlib import Path

# Environment detection
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY and not IS_PRODUCTION:
    print("[WARNING] GEMINI_API_KEY not set! Voice assistant will not work.")

# Audio Configuration (for STT only)
SAMPLE_RATE = int(os.environ.get("SAMPLE_RATE", "16000"))
CHANNELS = int(os.environ.get("CHANNELS", "1"))
SAMPLE_WIDTH = int(os.environ.get("SAMPLE_WIDTH", "2"))

# AI Configuration
MAX_GEMINI_WORDS = int(os.environ.get("MAX_GEMINI_WORDS", "50"))
CANDIDATE_MODELS = ["gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-1.5-flash"]

SYSTEM_PROMPT = """
You are a smart home assistant. STRICTLY follow these rules:
1. Reply ONLY in Hinglish using LATIN SCRIPT (Roman alphabet). NEVER use Devanagari (Hindi script).
2. Maximum 15 words.
3. If the user asks to turn light/fan ON or OFF, you MUST include the exact English phrase "light on", "light off", "fan on", or "fan off" in your reply.
4. Always be helpful and concise.
"""

# ESP32 Configuration
ESP32_SENSOR_URL = os.environ.get("ESP32_SENSOR_URL", "http://192.168.105.42")

# Server Configuration
PORT = int(os.environ.get("PORT", "8000"))
HOST = os.environ.get("HOST", "0.0.0.0")
