from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
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
    print("[RELAY] ESP32 #2 Relay Client connected via WebSocket")
    try:
        while True:
            data = await websocket.receive_text()
            print(f"[RELAY] WS received: {data}")
    except WebSocketDisconnect:
        relay_clients.remove(websocket)
        print("[RELAY] ESP32 #2 Relay Client disconnected")

async def send_relay_command(device: str, state: bool):
    relay_service.set_relay_state(device, state)
    command_json = {"device": device, "state": state}
    print(f"[RELAY] Sending command: {command_json}")

    # Try WebSocket first (new ESP32 firmware)
    ws_sent = False
    for client in relay_clients:
        try:
            await client.send_json(command_json)
            ws_sent = True
            print(f"[RELAY] Command sent via WebSocket")
        except Exception as e:
            print(f"[ERROR] [RELAY] WS Send failed: {e}")

    # Skip HTTP fallback in production (Render can't reach local ESP32)
    if not ws_sent:
        print(f"[RELAY] No WS clients connected - ESP32 #2 relay not available")
        print(f"[RELAY] To fix: Upload WebSocket-enabled code to ESP32 #2")

# ==========================================
# NEW BACKEND ENDPOINTS
# ==========================================

@router.post("/sensors/data")
async def push_sensor_data(data: SensorData):
    print(f"[SENSORS] Data received: {data}")
    relay_service.set_sensor_data(data.dict())
    return {"status": "ok"}

@router.get("/sensors/latest")
async def get_latest_sensors():
    print("[SENSORS] Latest data requested")
    return relay_service.get_sensor_data()

@router.post("/relay/set")
async def set_relay(command: RelayCommand):
    print(f"[RELAY] Set requested: {command}")
    await send_relay_command(command.device, command.state)
    return {"status": "ok"}

# ==========================================
# COMPAT: Old Flutter BackendApiService routes
# ==========================================

@router.get("/api/sensor/data")
async def compat_get_sensor_data():
    """Flutter BackendApiService calls GET /api/sensor/data"""
    print("[APP] [COMPAT] GET /api/sensor/data")
    data = relay_service.get_sensor_data()
    relays = relay_service.get_relay_state()
    return {
        "temperature": data.get("temperature", 0),
        "humidity": data.get("humidity", 0),
        "mqAnalog": data.get("mqAnalog", 0),
        "mqDigital": data.get("mqDigital", 0),
        "ldr": data.get("ldr", 0),
        "gas_analog": data.get("mqAnalog", 0),
        "gas_digital": data.get("mqDigital", 0),
        "light_level": data.get("ldr", 0),
        "light": relays.get("light", False),
        "fan": relays.get("fan", False),
    }

@router.post("/api/device/control")
async def compat_device_control(request: Request):
    """Flutter BackendApiService calls POST /api/device/control with {device, action}"""
    try:
        body = await request.json()
        device = body.get("device", "")
        action = body.get("action", "")
        print(f"[APP] [COMPAT] POST /api/device/control: device={device}, action={action}")

        state = True if action == "on" else False
        await send_relay_command(device, state)

        return {"status": "ok", "message": f"{device} turned {action}"}
    except Exception as e:
        print(f"[ERROR] [COMPAT] device control failed: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/api/device/status")
async def compat_get_device_status():
    """Flutter BackendApiService calls GET /api/device/status"""
    print("[APP] [COMPAT] GET /api/device/status")
    relays = relay_service.get_relay_state()
    return {
        "light": relays.get("light", False),
        "fan": relays.get("fan", False),
        "wifi_connected": True,
    }

@router.post("/api/device/status")
async def compat_post_device_status(request: Request):
    """Old ESP32 pushes device status via POST /api/device/status"""
    try:
        body = await request.json()
        print(f"[APP] [COMPAT] POST /api/device/status received: {body}")
        if "light" in body:
            relay_service.set_relay_state("light", bool(body["light"]))
        if "fan" in body:
            relay_service.set_relay_state("fan", bool(body["fan"]))
    except Exception as e:
        print(f"[ERROR] [COMPAT] device status parse failed: {e}")
    return {
        "sensors": relay_service.get_sensor_data(),
        "relays": relay_service.get_relay_state()
    }

@router.get("/api/device/ping")
async def compat_device_ping():
    """Flutter BackendApiService calls GET /api/device/ping"""
    print("[APP] [COMPAT] GET /api/device/ping")
    return {"status": "ok", "latency_ms": 1}

@router.get("/health")
async def health_check():
    """Flutter BackendApiService calls GET /health"""
    print("[APP] Health check")
    return {"status": "healthy", "backend": "online"}

@router.post("/api/sensors/update")
async def compat_sensor_update(request: Request):
    """Old ESP32/Flutter pushes sensor data via POST /api/sensors/update"""
    try:
        body = await request.json()
        print(f"[SENSORS] [COMPAT] /api/sensors/update received: {body}")
        mapped = {
            "mqAnalog": body.get("mqAnalog", body.get("mq_analog", body.get("gas_analog", 0))),
            "mqDigital": body.get("mqDigital", body.get("mq_digital", body.get("gas_digital", 0))),
            "ldr": body.get("ldr", body.get("light_level", 0)),
            "temperature": body.get("temperature", body.get("temp", 0.0)),
            "humidity": body.get("humidity", body.get("hum", 0.0)),
        }
        relay_service.set_sensor_data(mapped)
        return {"status": "ok"}
    except Exception as e:
        print(f"[ERROR] [COMPAT] sensor update parse failed: {e}")
        return {"status": "ok"}

# ==========================================
# COMPAT: Old Flutter ESP32ApiService routes
# (Flutter previously talked directly to ESP32,
#  now routed through backend)
# ==========================================

@router.get("/light/on")
async def compat_light_on():
    print("[RELAY] [COMPAT] GET /light/on")
    await send_relay_command("light", True)
    return "Light ON"

@router.get("/light/off")
async def compat_light_off():
    print("[RELAY] [COMPAT] GET /light/off")
    await send_relay_command("light", False)
    return "Light OFF"

@router.get("/fan/on")
async def compat_fan_on():
    print("[RELAY] [COMPAT] GET /fan/on")
    await send_relay_command("fan", True)
    return "Fan ON"

@router.get("/fan/off")
async def compat_fan_off():
    print("[RELAY] [COMPAT] GET /fan/off")
    await send_relay_command("fan", False)
    return "Fan OFF"

@router.get("/sensor")
async def compat_sensor():
    """Old ESP32ApiService calls GET /sensor"""
    print("[SENSORS] [COMPAT] GET /sensor")
    data = relay_service.get_sensor_data()
    return {
        "mqAnalog": data.get("mqAnalog", 0),
        "mqDigital": data.get("mqDigital", 0),
        "ldr": data.get("ldr", 0),
        "temperature": data.get("temperature", 0),
        "humidity": data.get("humidity", 0),
    }

@router.get("/status")
async def compat_status():
    """Old ESP32ApiService calls GET /status"""
    print("[APP] [COMPAT] GET /status")
    relays = relay_service.get_relay_state()
    return {
        "light": relays.get("light", False),
        "fan": relays.get("fan", False),
        "wifi_connected": True,
        "uptime": 0,
    }
