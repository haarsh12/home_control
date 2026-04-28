from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from services import stt_service, gemini_service, tts_service, relay_service, laptop_service
from routers import laptop
import httpx
import config

router = APIRouter()

@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Client connected")
    
    state = "IDLE"
    audio_buffer = bytearray()
    connection_active = True
    
    async def safe_send_text(text: str):
        """Safely send text, catching disconnection errors"""
        if not connection_active:
            return False
        try:
            await websocket.send_text(text)
            return True
        except Exception as e:
            print(f"[WS] Failed to send text: {e}")
            return False
    
    async def safe_send_bytes(data: bytes):
        """Safely send bytes, catching disconnection errors"""
        if not connection_active:
            return False
        try:
            await websocket.send_bytes(data)
            return True
        except Exception as e:
            print(f"[WS] Failed to send bytes: {e}")
            return False
    
    try:
        while connection_active:
            try:
                message = await websocket.receive()
            except RuntimeError as e:
                if "disconnect" in str(e).lower():
                    print("[WS] Client disconnected during receive")
                    connection_active = False
                    break
                raise
            
            # Check for disconnect message
            if message.get("type") == "websocket.disconnect":
                print("[WS] Received disconnect message")
                connection_active = False
                break
            
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
                        await safe_send_text("LCD:Too short")
                        state = "IDLE"
                        continue
                    
                    # Process audio in background
                    try:
                        user_text = await asyncio.to_thread(stt_service.transcribe_wav, bytes(audio_buffer))
                        
                        if not user_text or user_text.strip() == "":
                            print("[ERROR] [WS] STT returned empty text")
                            await safe_send_text("LCD:Not understood")
                            state = "IDLE"
                            continue
                        
                        print(f"[WS] Transcribed: {user_text}")
                        
                        # Check if this is a laptop command
                        laptop_command = laptop_service.parse_laptop_command(user_text)
                        
                        if laptop_command:
                            print(f"[WS] Detected laptop command: {laptop_command}")
                            
                            # Send command to connected laptops
                            sent = await laptop.send_command_to_laptops(laptop_command)
                            
                            if sent:
                                # Acknowledge to user
                                ai_text = "Okay, opening on laptop"
                                if laptop_command["action"] == "open_youtube":
                                    ai_text = f"Playing {laptop_command.get('query', 'video')} on laptop"
                                elif laptop_command["action"] == "google_search":
                                    ai_text = f"Searching {laptop_command.get('query', 'that')} on laptop"
                                elif laptop_command["action"] == "open_app":
                                    ai_text = f"Opening {laptop_command.get('app', 'app')} on laptop"
                                
                                print(f"[WS] Laptop command sent: {ai_text}")
                            else:
                                ai_text = "No laptop connected"
                                print("[WS] No laptop connected to execute command")
                            
                            # Send response to ESP32
                            if not await safe_send_text(f"LCD:{ai_text}"):
                                print("[ERROR] [WS] Failed to send LCD text, connection lost")
                                connection_active = False
                                break
                            
                            state = "IDLE"
                            continue
                        
                        # Not a laptop command, proceed with normal flow
                        print("[WS] Not a laptop command, processing normally")
                        
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
                        
                        # Generate TTS audio (optional - will be empty if TTS unavailable)
                        pcm_bytes = await asyncio.to_thread(tts_service.text_to_wav_bytes, ai_text)
                        
                        # Send LCD text (always)
                        if not await safe_send_text(f"LCD:{ai_text}"):
                            print("[ERROR] [WS] Failed to send LCD text, connection lost")
                            connection_active = False
                            break
                        print(f"[WS] Sent LCD: {ai_text}")
                        await asyncio.sleep(0.05)
                        
                        # Send audio only if TTS generated it
                        if pcm_bytes and len(pcm_bytes) > 0:
                            # Send audio start marker
                            if not await safe_send_text("AUDIO_START"):
                                print("[ERROR] [WS] Failed to send AUDIO_START, connection lost")
                                connection_active = False
                                break
                            print("[WS] Sent AUDIO_START")
                            await asyncio.sleep(0.05)
                            
                            # Send audio length
                            if not await safe_send_text(str(len(pcm_bytes))):
                                print("[ERROR] [WS] Failed to send audio length, connection lost")
                                connection_active = False
                                break
                            print(f"[WS] Sent audio length: {len(pcm_bytes)}")
                            await asyncio.sleep(0.05)
                            
                            # Send audio data in chunks
                            chunk_size = 512
                            for i in range(0, len(pcm_bytes), chunk_size):
                                chunk = pcm_bytes[i:i+chunk_size]
                                if not await safe_send_bytes(chunk):
                                    print("[ERROR] [WS] Failed to send audio chunk, connection lost")
                                    connection_active = False
                                    break
                                await asyncio.sleep(0.01)
                            
                            if connection_active:
                                print("[WS] Audio transmission complete")
                        else:
                            print("[WS] TTS not available - text-only mode (LCD already sent)")
                            # ESP32 will just show the text on LCD without audio playback
                        
                    except Exception as e:
                        print(f"[ERROR] [WS] Processing error: {e}")
                        import traceback
                        traceback.print_exc()
                        await safe_send_text("LCD:Error occurred")
                    
                    state = "IDLE"
                    
                elif text == "PING":
                    await safe_send_text("PONG")

            elif "bytes" in message:
                if state == "RECORDING":
                    audio_buffer.extend(message["bytes"])
                    
    except WebSocketDisconnect:
        print("[WS] Client disconnected normally")
    except Exception as e:
        print(f"[ERROR] [WS] Exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        connection_active = False
        print("[WS] Connection cleanup complete")
