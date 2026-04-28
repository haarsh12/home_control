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
    if not pcm_data or len(pcm_data) < 1000:
        print(f"[ERROR] [STT] Insufficient audio data: {len(pcm_data) if pcm_data else 0} bytes")
        return ""
    
    temp_wav = tempfile.mktemp(suffix=".wav")
    try:
        save_wav(pcm_data, temp_wav)
        
        # Check if file was created successfully
        if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) < 1000:
            print(f"[ERROR] [STT] WAV file too small or not created")
            return ""
        
        print(f"[STT] Processing audio file: {os.path.getsize(temp_wav)} bytes")
        
        r = sr.Recognizer()
        r.energy_threshold = 300  # Lower threshold for better sensitivity
        r.dynamic_energy_threshold = True
        
        with sr.AudioFile(temp_wav) as source:
            # Adjust for ambient noise
            r.adjust_for_ambient_noise(source, duration=0.2)
            audio = r.record(source)
        
        # Try Hindi first
        try:
            txt = r.recognize_google(audio, language="hi-IN")
            if txt and txt.strip():
                print(f"[STT] Hindi: {txt}")
                return txt.strip()
        except sr.UnknownValueError:
            print("[STT] hi-IN: Could not understand audio")
        except sr.RequestError as e:
            print(f"[ERROR] [STT] hi-IN API error: {e}")
        except Exception as e:
            print(f"[ERROR] [STT] hi-IN failed: {e}")

        # Try English
        try:
            txt = r.recognize_google(audio, language="en-US")
            if txt and txt.strip():
                print(f"[STT] English: {txt}")
                return txt.strip()
        except sr.UnknownValueError:
            print("[STT] en-US: Could not understand audio")
        except sr.RequestError as e:
            print(f"[ERROR] [STT] en-US API error: {e}")
        except Exception as e:
            print(f"[ERROR] [STT] en-US failed: {e}")
            
    except Exception as e:
        print(f"[ERROR] [STT] General error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except:
                pass
    
    return ""
