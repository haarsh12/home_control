from pydantic import BaseModel

class SensorData(BaseModel):
    mqAnalog: int
    mqDigital: int
    ldr: int
    temperature: float
    humidity: float

class RelayCommand(BaseModel):
    device: str
    state: bool
