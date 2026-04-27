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
                    print("[WS] Recording stopped, Processing started")
                    
                    user_text = await asyncio.to_thread(stt_service.transcribe_wav, bytes(audio_buffer))
                    if user_text:
                        sensor_data = relay_service.get_sensor_data()
                        relay_state = relay_service.get_relay_state()
                        
                        ai_text, relay_commands = await asyncio.to_thread(
                            gemini_service.ask_gemini, user_text, sensor_data, relay_state
                        )
                        
                        if relay_commands:
                            from routers.sensors import send_relay_command
                            for cmd in relay_commands:
                                await send_relay_command(cmd["device"], cmd["state"])
                        
                        pcm_bytes = await asyncio.to_thread(tts_service.text_to_wav_bytes, ai_text)
                        
                        await websocket.send_text(f"LCD:{ai_text}")
                        print(f"[WS] Sent LCD: {ai_text}")
                        
                        await websocket.send_text("AUDIO_START")
                        print("[WS] Sent AUDIO_START")
                        
                        await websocket.send_text(str(len(pcm_bytes)))
                        print(f"[WS] Sent audio length: {len(pcm_bytes)}")
                        
                        chunk_size = 256
                        for i in range(0, len(pcm_bytes), chunk_size):
                            await websocket.send_bytes(pcm_bytes[i:i+chunk_size])
                            await asyncio.sleep(0.005)
                            
                        print("[WS] Audio transmission complete")
                        
                    state = "IDLE"

            elif "bytes" in message:
                if state == "RECORDING":
                    audio_buffer.extend(message["bytes"])
                    
    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[ERROR] [WS] Exception: {e}")
