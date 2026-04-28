# Smart Home Backend API

Backend API for ESP32-based Smart Home system with Voice Assistant, Sensor Monitoring, and Relay Control.

## Features

- 🎤 Voice Assistant with Speech-to-Text (Google) and Text-to-Speech (gTTS)
- 🤖 AI-powered responses using Google Gemini
- 📊 Real-time sensor data monitoring (Temperature, Humidity, Gas, Light)
- 💡 Relay control for lights and fans
- 🔌 WebSocket support for real-time communication
- 📱 Compatible with Flutter mobile app
- 🔧 Compatible with ESP32 devices

## Tech Stack

- **Framework**: FastAPI
- **WebSockets**: Native FastAPI WebSocket support
- **Speech Recognition**: Google Speech Recognition API
- **Text-to-Speech**: Google Text-to-Speech (gTTS)
- **AI**: Google Gemini API
- **Audio Processing**: pydub, ffmpeg

## Prerequisites

- Python 3.11+
- ffmpeg (for audio processing)
- Google Gemini API Key

## Local Development Setup

### Windows

1. **Clone the repository**
   ```bash
   cd home_automation/backend
   ```

2. **Run setup script**
   ```bash
   setup_venv.bat
   ```

3. **Create .env file**
   ```bash
   copy .env.example .env
   ```

4. **Edit .env and add your API key**
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

5. **Run the server**
   ```bash
   venv\Scripts\activate
   python main.py
   ```

### Linux/Mac

1. **Clone the repository**
   ```bash
   cd home_automation/backend
   ```

2. **Run setup script**
   ```bash
   chmod +x setup_venv.sh
   ./setup_venv.sh
   ```

3. **Create .env file**
   ```bash
   cp .env.example .env
   ```

4. **Edit .env and add your API key**
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

5. **Run the server**
   ```bash
   source venv/bin/activate
   python main.py
   ```

## Deployment on Render

### Method 1: Using render.yaml (Recommended)

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

2. **Create new Web Service on Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml`

3. **Set Environment Variables**
   - `GEMINI_API_KEY`: Your Google Gemini API key (required)
   - Other variables are pre-configured in render.yaml

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment to complete

### Method 2: Manual Configuration

1. **Create new Web Service**
   - Name: `smart-home-backend`
   - Environment: `Python 3`
   - Build Command: `./build.sh`
   - Start Command: `uvicorn main:fastapi_app --host 0.0.0.0 --port $PORT`

2. **Set Environment Variables**
   ```
   ENVIRONMENT=production
   GEMINI_API_KEY=your_api_key_here
   PORT=8000
   HOST=0.0.0.0
   SAMPLE_RATE=16000
   CHANNELS=1
   SAMPLE_WIDTH=2
   MAX_GEMINI_WORDS=50
   ```

3. **Deploy**

## API Endpoints

### Health Check
- `GET /` - Root endpoint with API info
- `GET /health` - Health check endpoint

### Sensors
- `GET /api/sensor/data` - Get latest sensor data
- `POST /api/sensors/update` - Update sensor data (from ESP32)
- `GET /sensors/latest` - Get latest sensor data (new format)
- `POST /sensors/data` - Push sensor data (new format)

### Relay Control
- `POST /api/device/control` - Control devices (light/fan)
- `GET /api/device/status` - Get device status
- `POST /relay/set` - Set relay state (new format)
- `GET /light/on` - Turn light on
- `GET /light/off` - Turn light off
- `GET /fan/on` - Turn fan on
- `GET /fan/off` - Turn fan off

### WebSocket Endpoints
- `WS /ws/voice` - Voice assistant WebSocket
- `WS /ws/relay` - Relay control WebSocket

## ESP32 Configuration

Update your ESP32 code with the deployed backend URL:

```cpp
// For local development
const char* backend_ip = "192.168.x.x";  // Your local IP

// For production (Render)
const char* backend_url = "your-app.onrender.com";
const int backend_port = 443;  // HTTPS
const bool use_ssl = true;
```

## Flutter App Configuration

Update the Flutter app's API service:

```dart
// lib/config/api_config.dart
class ApiConfig {
  // For local development
  static const String baseUrl = 'http://192.168.x.x:8000';
  
  // For production (Render)
  static const String baseUrl = 'https://your-app.onrender.com';
  
  static const String wsUrl = 'wss://your-app.onrender.com';
}
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Environment mode | `development` | No |
| `GEMINI_API_KEY` | Google Gemini API key | - | Yes |
| `PORT` | Server port | `8000` | No |
| `HOST` | Server host | `0.0.0.0` | No |
| `SAMPLE_RATE` | Audio sample rate | `16000` | No |
| `CHANNELS` | Audio channels | `1` | No |
| `SAMPLE_WIDTH` | Audio sample width | `2` | No |
| `MAX_GEMINI_WORDS` | Max words in AI response | `50` | No |
| `ESP32_SENSOR_URL` | ESP32 device URL (local) | - | No |

## Troubleshooting

### FFmpeg not found
- **Local**: Install ffmpeg and add to PATH
- **Render**: Automatically installed via build.sh

### GEMINI_API_KEY not set
- Add the environment variable in Render dashboard
- Or create `.env` file for local development

### WebSocket connection fails
- Check CORS settings in main.py
- Verify WebSocket URL uses `wss://` for HTTPS
- Check firewall settings

### Audio quality issues
- Adjust `SAMPLE_RATE` (default: 16000)
- Check microphone quality on ESP32
- Verify network bandwidth

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
```

### Linting
```bash
flake8 .
```

## Architecture

```
┌─────────────┐     WebSocket      ┌─────────────┐
│   ESP32     │◄──────────────────►│   Backend   │
│  (Voice)    │     /ws/voice      │   (Render)  │
└─────────────┘                    └─────────────┘
                                          ▲
┌─────────────┐     WebSocket            │
│   ESP32     │◄─────────────────────────┤
│ (Sensors)   │     /ws/relay            │
└─────────────┘                          │
                                         │
┌─────────────┐     HTTP/REST            │
│   Flutter   │◄─────────────────────────┘
│     App     │     /api/*
└─────────────┘
```

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.
