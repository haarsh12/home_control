"""
TTS Service - Text-only mode (no audio generation)
Audio generation disabled to avoid ffmpeg dependency on Render.
Only text will be sent to ESP32 LCD display.
"""

# TTS is disabled - text-only mode
TTS_AVAILABLE = False
TTS_ERROR_MESSAGE = "TTS disabled - text-only mode (no ffmpeg dependency)"

print(f"[TTS] Text-only mode enabled - no audio generation")

def text_to_wav_bytes(text: str) -> bytes:
    """
    Text-only mode - returns empty bytes.
    ESP32 will only display text on LCD without audio playback.
    """
    print(f"[TTS] Text-only mode: {text}")
    return b""

def is_tts_available() -> bool:
    """Check if TTS is available"""
    return TTS_AVAILABLE

def get_tts_status() -> dict:
    """Get TTS status information"""
    return {
        "available": TTS_AVAILABLE,
        "error": TTS_ERROR_MESSAGE
    }
