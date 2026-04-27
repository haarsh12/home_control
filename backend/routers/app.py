from fastapi import APIRouter
from services import relay_service
from models.schemas import RelayCommand
from routers.sensors import send_relay_command

router = APIRouter()

@router.get("/app/sensors")
async def get_app_sensors():
    print("[APP] Sensors requested")
    return {
        "sensors": relay_service.get_sensor_data(),
        "relays": relay_service.get_relay_state()
    }

@router.post("/app/relay")
async def app_set_relay(command: RelayCommand):
    print(f"[APP] Relay set requested: {command}")
    await send_relay_command(command.device, command.state)
    return {"status": "ok"}

@router.get("/app/status")
async def get_app_status():
    print("[APP] Status requested")
    return {
        "status": "online"
    }
