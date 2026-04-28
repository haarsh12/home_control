from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from services import stt_service, gemini_service, tts_service, relay_service
import httpx
import config

router = APIRouter()

@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Client connected")
    
    state = "IDLE"
    audio_buffer = bytearray()
    
    try:
        while True:
            message = await websocket.receive()
            
            if "text" in message:
                text = message["text"]
                
                if text == "START":
                    state = "RECORDING"
                    audio_buffer = bytearray()
                    print("[WS] Recording started")
                    
                elif text == "STOP":
                    state = "PROCESSING"
                    print(f"[WS] Recording stopped, Processing started. Buffer size: {len(audio_buffer)} bytes")
                    
                    # Check if we have enough audio data
                    if len(audio_buffer) < 1000:
                        print(f"[ERROR] [WS] Insufficient audio data: {len(audio_buffer)} bytes")
                        await websocket.send_text("LCD:Too short")
                        state = "IDLE"
                        continue
                    
                    # Process audio in background
                    try:
                        user_text = await asyncio.to_thread(stt_service.transcribe_wav, bytes(audio_buffer))
                        
                        if not user_text or user_text.strip() == "":
                            print("[ERROR] [WS] STT returned empty text")
                            await websocket.send_text("LCD:Not understood")
                            state = "IDLE"
                            continue
                        
                        print(f"[WS] Transcribed: {user_text}")
                        
                        # Get sensor and relay data
                        sensor_data = relay_service.get_sensor_data()
                        relay_state = relay_service.get_relay_state()
                        
                        # Get AI response
                        ai_text, relay_commands = await asyncio.to_thread(
                            gemini_service.ask_gemini, user_text, sensor_data, relay_state
                        )
                        
                        print(f"[WS] AI Response: {ai_text}")
                        
                        # Execute relay commands if any
                        if relay_commands:
                            from routers.sensors import send_relay_command
                            for cmd in relay_commands:
                                await send_relay_command(cmd["device"], cmd["state"])
                        
                        # Generate TTS audio
                        pcm_bytes = await asyncio.to_thread(tts_service.text_to_wav_bytes, ai_text)
                        
                        if not pcm_bytes or len(pcm_bytes) == 0:
                            print("[ERROR] [WS] TTS returned empty audio")
                            await websocket.send_text("LCD:TTS Error")
                            state = "IDLE"
                            continue
                        
                        # Send LCD text
                        await websocket.send_text(f"LCD:{ai_text}")
                        print(f"[WS] Sent LCD: {ai_text}")
                        await asyncio.sleep(0.05)
                        
                        # Send audio start marker
                        await websocket.send_text("AUDIO_START")
                        print("[WS] Sent AUDIO_START")
                        await asyncio.sleep(0.05)
                        
                        # Send audio length
                        await websocket.send_text(str(len(pcm_bytes)))
                        print(f"[WS] Sent audio length: {len(pcm_bytes)}")
                        await asyncio.sleep(0.05)
                        
                        # Send audio data in chunks
                        chunk_size = 512
                        for i in range(0, len(pcm_bytes), chunk_size):
                            chunk = pcm_bytes[i:i+chunk_size]
                            await websocket.send_bytes(chunk)
                            await asyncio.sleep(0.01)  # Slightly longer delay
                            
                        print("[WS] Audio transmission complete")
                        
                    except Exception as e:
                        print(f"[ERROR] [WS] Processing error: {e}")
                        import traceback
                        traceback.print_exc()
                        await websocket.send_text("LCD:Error occurred")
                    
                    state = "IDLE"
                    
                elif text == "PING":
                    await websocket.send_text("PONG")

            elif "bytes" in message:
                if state == "RECORDING":
                    audio_buffer.extend(message["bytes"])
                    
    except WebSocketDisconnect:
        print("[WS] Client disconnected normally")
    except Exception as e:
        print(f"[ERROR] [WS] Exception: {e}")
        import traceback
        traceback.print_exc()
