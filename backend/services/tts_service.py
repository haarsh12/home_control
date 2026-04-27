from gtts import gTTS
from pydub import AudioSegment
import io
import wave
import tempfile
import os
import config

def text_to_wav_bytes(text: str) -> bytes:
    try:
        tts = gTTS(text=text, lang="hi")
        mp3_buffer = io.BytesIO()
        tts.write_to_fp(mp3_buffer)
        mp3_buffer.seek(0)

        audio = AudioSegment.from_mp3(mp3_buffer)
        audio = audio.set_frame_rate(config.SAMPLE_RATE)
        audio = audio.set_channels(config.CHANNELS)
        audio = audio.set_sample_width(config.SAMPLE_WIDTH)

        temp_wav = tempfile.mktemp(suffix=".wav")
        audio.export(temp_wav, format="wav")

        with wave.open(temp_wav, 'rb') as wf:
            pcm_data = wf.readframes(wf.getnframes())

        os.remove(temp_wav)
        
        print(f"[TTS] byte count: {len(pcm_data)}")
        return pcm_data
    except Exception as e:
        print(f"[ERROR] [TTS] Exception: {e}")
        return b""
