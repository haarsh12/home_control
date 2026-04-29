from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
from services import relay_service
from models.schemas import SensorData, RelayCommand
import httpx
import config

router = APIRouter()

relay_clients = []

@router.websocket("/ws/relay")
async def relay_websocket(websocket: WebSocket):
    await websocket.accept()
    relay_clients.append(websocket)
    print("[RELAY] ESP32 Relay Client connected via WebSocket")
    try:
        while True:
            data = await websocket.receive_text()
            print(f"[RELAY] WS received: {data}")
    except WebSocketDisconnect:
        relay_clients.remove(websocket)
        print("[RELAY] ESP32 Relay Client disconnected")

async def send_relay_command(device: str, state: bool):
    """Send relay command via WebSocket or HTTP fallback"""
    if device not in ["light", "fan"]:
        raise HTTPException(status_code=400, detail=f"Invalid device: {device}")
    
    relay_service.set_relay_state(device, state)
    command_json = {"device": device, "state": state}
    print(f"[RELAY] Sending command: {command_json}")

    # Try WebSocket first (preferred method)
    ws_sent = False
    for client in relay_clients[:]:  # Create copy to avoid modification during iteration
        try:
            await client.send_json(command_json)
            ws_sent = True
            print(f"[RELAY] Command sent via WebSocket")
            break
        except Exception as e:
            print(f"[ERROR] [RELAY] WS Send failed: {e}")
            relay_clients.remove(client)

    # HTTP fallback to ESP32
    if not ws_sent:
        print(f"[RELAY] No WS clients, using HTTP fallback")
        state_str = "on" if state else "off"
        url = f"{config.ESP32_SENSOR_URL}/{device}/{state_str}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as http_client:
                response = await http_client.get(url)
                print(f"[RELAY] HTTP -> GET {url} -> {response.status_code}")
                if response.status_code != 200:
                    raise HTTPException(status_code=502, detail="ESP32 command failed")
        except httpx.ConnectError:
            print(f"[ERROR] [RELAY] Cannot connect to ESP32 at {url}")
            raise HTTPException(status_code=503, detail="ESP32 not reachable")
        except Exception as e:
            print(f"[ERROR] [RELAY] HTTP fallback failed: {e}")
            raise HTTPException(status_code=502, detail="Relay command failed")

# ==========================================
# CORE API ENDPOINTS (Used by Flutter App)
# ==========================================

@router.post("/sensors/data")
async def push_sensor_data(data: SensorData):
    """Accept sensor data from ESP32"""
    print(f"[SENSORS] Data received: {data}")
    relay_service.set_sensor_data(data.dict())
    return {"status": "ok"}

@router.get("/sensors/latest")
async def get_latest_sensors():
    """Get latest sensor readings"""
    print("[SENSORS] Latest data requested")
    return relay_service.get_sensor_data()

@router.post("/relay/set")
async def set_relay(command: RelayCommand):
    """Set relay state (light/fan on/off)"""
    print(f"[RELAY] Set requested: {command}")
    await send_relay_command(command.device, command.state)
    return {"status": "ok"}

# ==========================================
# FLUTTER APP API ENDPOINTS
# ==========================================

@router.get("/api/sensor/data")
async def get_sensor_data():
    """Flutter app: Get sensor data with device status"""
    print("[APP] GET /api/sensor/data")
    sensor_data = relay_service.get_sensor_data()
    relay_data = relay_service.get_relay_state()
    
    return {
        "temperature": sensor_data.get("temperature", 0.0),
        "humidity": sensor_data.get("humidity", 0.0),
        "mqAnalog": sensor_data.get("mqAnalog", 0),
        "mqDigital": sensor_data.get("mqDigital", 0),
        "ldr": sensor_data.get("ldr", 0),
        "light": relay_data.get("light", False),
        "fan": relay_data.get("fan", False),
    }

@router.post("/api/device/control")
async def device_control(request: Request):
    """Flutter app: Control devices (light/fan)"""
    try:
        body = await request.json()
        device = body.get("device", "").lower()
        action = body.get("action", "").lower()
        
        if not device or not action:
            raise HTTPException(status_code=400, detail="Missing device or action")
        
        if device not in ["light", "fan"]:
            raise HTTPException(status_code=400, detail=f"Invalid device: {device}")
        
        if action not in ["on", "off"]:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
        
        print(f"[APP] Device control: {device} -> {action}")
        state = action == "on"
        await send_relay_command(device, state)
        
        return {"status": "ok", "message": f"{device} turned {action}"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Device control failed: {e}")
        raise HTTPException(status_code=500, detail="Device control failed")

@router.get("/api/device/status")
async def get_device_status():
    """Flutter app: Get device status"""
    print("[APP] GET /api/device/status")
    relays = relay_service.get_relay_state()
    return {
        "light": relays.get("light", False),
        "fan": relays.get("fan", False),
        "wifi_connected": True,
    }

@router.get("/api/device/ping")
async def device_ping():
    """Flutter app: Ping test"""
    print("[APP] Device ping")
    return {"status": "ok", "latency_ms": 1}

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    print("[APP] Health check")
    return {"status": "healthy", "backend": "online"}

# ==========================================
# ESP32 COMPATIBILITY ENDPOINTS
# ==========================================

@router.post("/api/device/status")
async def esp32_device_status_update(request: Request):
    """ESP32: Update device status"""
    try:
        body = await request.json()
        print(f"[ESP32] Device status update: {body}")
        
        if "light" in body:
            relay_service.set_relay_state("light", bool(body["light"]))
        if "fan" in body:
            relay_service.set_relay_state("fan", bool(body["fan"]))
            
        return {"status": "ok"}
    except Exception as e:
        print(f"[ERROR] ESP32 status update failed: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/api/sensors/update")
async def esp32_sensor_update(request: Request):
    """ESP32: Update sensor data"""
    try:
        body = await request.json()
        print(f"[ESP32] Sensor update: {body}")
        
        # Map various sensor field names to standard format
        mapped_data = {
            "mqAnalog": body.get("mqAnalog", body.get("mq_analog", body.get("gas_analog", 0))),
            "mqDigital": body.get("mqDigital", body.get("mq_digital", body.get("gas_digital", 0))),
            "ldr": body.get("ldr", body.get("light_level", 0)),
            "temperature": float(body.get("temperature", body.get("temp", 0.0))),
            "humidity": float(body.get("humidity", body.get("hum", 0.0))),
        }
        
        relay_service.set_sensor_data(mapped_data)
        return {"status": "ok"}
    except Exception as e:
        print(f"[ERROR] ESP32 sensor update failed: {e}")
        return {"status": "error", "message": str(e)}
