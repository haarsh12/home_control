# Home Automation + AI Voice Assistant

This project is a unified Home Automation and AI Voice Assistant system using FastAPI, WebSockets, and Gemini.

## Folder Structure

- `backend/`: FastAPI application handling STT, TTS, Gemini AI, and managing relay states.
- `esp32_voice_speaker/`: Code for the ESP32 handling mic/speaker and communicating with the backend over WebSockets.
- `esp32_sensors_relay/`: Code for the ESP32 handling sensors and relays, pushing data to the backend via HTTP and listening to relay commands over WebSockets.

## 1. Backend Setup

### Prerequisites
- Python 3.9+
- FFmpeg installed

### Steps

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure `backend/config.py`:
   - Set `FFMPEG_PATH` to the absolute path of your FFmpeg `bin` folder.
   - Set `GEMINI_API_KEY` to your valid Gemini API key.
5. Run the server:
   ```bash
   python main.py
   ```
   The backend will print its IP address on startup (e.g., `192.168.x.x`). You will need this IP for the ESP32s and Flutter App.

## 2. Flashing the ESP32s

### ESP32 Voice Speaker
1. Open `esp32_voice_speaker/esp32_voice_speaker.ino` in Arduino IDE.
2. Ensure you have the `WebSockets` library installed (by Links2004).
3. Update the `ssid` and `password` variables with your WiFi credentials.
4. Update `backend_ip` with the IP address printed by the FastAPI backend on startup.
5. Select your ESP32 board and port, then click **Upload**.

### ESP32 Sensors & Relay
1. Open `esp32_sensors_relay/esp32_sensors_relay.ino` in Arduino IDE.
2. Ensure you have the `WebSockets` and `ArduinoJson` libraries installed.
3. Update the `ssid` and `password` variables with your WiFi credentials.
4. Update `backend_ip` with the IP address printed by the FastAPI backend on startup.
5. Select your ESP32 board and port, then click **Upload**.

## 3. Flutter App Integration

Your Flutter app should make the following requests to the FastAPI backend:
- **Get Sensors & Relays**: `GET http://<backend_ip>:8000/app/sensors`
- **Control Relay**: `POST http://<backend_ip>:8000/app/relay` with body `{"device": "light"|"fan", "state": true|false}`
