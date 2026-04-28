import os

# FFMPEG_PATH must be set from config.py at startup
FFMPEG_PATH = r"C:\Users\LOQ\Downloads\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCy866Bzgsg7wXbCQBOJcB-J_hzKUPPQM0")

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2
MAX_GEMINI_WORDS = 50
CANDIDATE_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]
SYSTEM_PROMPT = """
You are a smart home assistant. STRICTLY follow these rules:
1. Reply ONLY in Hinglish using LATIN SCRIPT (Roman alphabet). NEVER use Devanagari (Hindi script).
2. Maximum 15 words.
3. If the user asks to turn light/fan ON or OFF, you MUST include the exact English phrase "light on", "light off", "fan on", or "fan off" in your reply.
4. Always be helpful and concise.
"""
ESP32_SENSOR_URL = "http://192.168.105.42"
