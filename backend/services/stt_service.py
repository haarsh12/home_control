import speech_recognition as sr
import wave
import tempfile
import os
import config

def save_wav(pcm_data, filename):
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(config.CHANNELS)
        wf.setsampwidth(config.SAMPLE_WIDTH)
        wf.setframerate(config.SAMPLE_RATE)
        wf.writeframes(pcm_data)

def transcribe_wav(pcm_data: bytes) -> str:
    temp_wav = tempfile.mktemp(suffix=".wav")
    save_wav(pcm_data, temp_wav)
    r = sr.Recognizer()
    try:
        with sr.AudioFile(temp_wav) as source:
            audio = r.record(source)
        try:
            txt = r.recognize_google(audio, language="hi-IN")
            if txt.strip():
                print(f"[STT] {txt}")
                return txt
        except Exception as e:
            print(f"[ERROR] [STT] hi-IN failed: {e}")

        try:
            txt = r.recognize_google(audio, language="en-US")
            if txt.strip():
                print(f"[STT] {txt}")
                return txt
        except Exception as e:
            print(f"[ERROR] [STT] en-US failed: {e}")
    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
    return ""
