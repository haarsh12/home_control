relay_state = {"light": False, "fan": False}
latest_sensor_data = {"mqAnalog": 0, "mqDigital": 0, "ldr": 0, "temperature": 0.0, "humidity": 0.0}

def get_relay_state():
    return relay_state

def set_relay_state(device: str, state: bool):
    if device in relay_state:
        relay_state[device] = state

def get_sensor_data():
    return latest_sensor_data

def set_sensor_data(data: dict):
    global latest_sensor_data
    latest_sensor_data = data
