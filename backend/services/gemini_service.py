from google import genai
import config
import re

# Initialize Gemini client only if API key is available
GEMINI_AVAILABLE = bool(config.GEMINI_API_KEY)
client = None

if GEMINI_AVAILABLE:
    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        print("[GEMINI] Client initialized successfully")
    except Exception as e:
        print(f"[ERROR] [GEMINI] Failed to initialize: {e}")
        GEMINI_AVAILABLE = False
else:
    print("[WARNING] [GEMINI] API key not set - AI responses disabled")

def detect_relay_commands(user_text: str, ai_text: str):
    """Detect relay commands from BOTH user's original STT text AND AI response text. answer in only short 15 words max and in latin script only dont use devnagri script also give answers to users general query """
    relay_commands = []
    
    # Combine both texts for detection
    combined = (user_text + " " + ai_text).lower()
    
    # --- LIGHT detection ---
    light_on_keywords = [
        "light on", "light chalu", "light chalao", "light jala",
        "batti on", "batti chalu", "batti jala",
        "लाइट ऑन", "लाइट चालू", "लाइट जला", "बत्ती चालू", "बत्ती जला",
        "light kar do", "light karo", "light on karo", "light on kar",
        "लाइट चालू करो", "लाइट ऑन करो",
    ]
    light_off_keywords = [
        "light off", "light band", "light bujha", "light bujhao",
        "batti off", "batti band", "batti bujha",
        "लाइट ऑफ", "लाइट बंद", "लाइट बुझा", "बत्ती बंद", "बत्ती बुझा",
        "light off karo", "light off kar", "light band karo",
        "लाइट ऑफ करो", "लाइट बंद करो",
    ]
    
    # Check OFF first (more specific), then ON
    light_off = any(kw in combined for kw in light_off_keywords)
    light_on = any(kw in combined for kw in light_on_keywords)
    
    if light_off:
        relay_commands.append({"device": "light", "state": False})
    elif light_on:
        relay_commands.append({"device": "light", "state": True})
    
    # --- FAN detection ---
    fan_on_keywords = [
        "fan on", "fan chalu", "fan chalao",
        "pankha on", "pankha chalu", "pankha chalao",
        "पंखा ऑन", "पंखा चालू", "फैन ऑन", "फैन चालू",
        "fan on karo", "fan chalu karo",
        "पंखा चालू करो", "फैन ऑन करो",
    ]
    fan_off_keywords = [
        "fan off", "fan band",
        "pankha off", "pankha band",
        "पंखा ऑफ", "पंखा बंद", "फैन ऑफ", "फैन बंद",
        "fan off karo", "fan band karo",
        "पंखा बंद करो", "फैन ऑफ करो",
    ]
    
    fan_off = any(kw in combined for kw in fan_off_keywords)
    fan_on = any(kw in combined for kw in fan_on_keywords)
    
    if fan_off:
        relay_commands.append({"device": "fan", "state": False})
    elif fan_on:
        relay_commands.append({"device": "fan", "state": True})
    
    return relay_commands

def ask_gemini(user_text: str, sensor_data: dict, relay_state: dict):
    if not GEMINI_AVAILABLE:
        print("[GEMINI] API not available - using fallback response")
        # Detect commands from user text only
        relay_commands = detect_relay_commands(user_text, "")
        return "Samajh gaya", relay_commands
    
    light_status = "ON" if relay_state.get("light") else "OFF"
    fan_status = "ON" if relay_state.get("fan") else "OFF"
    
    context = (f"Current sensors: temp={sensor_data.get('temperature')}, "
               f"humidity={sensor_data.get('humidity')}, "
               f"mq_analog={sensor_data.get('mqAnalog')}, "
               f"mq_digital={sensor_data.get('mqDigital')}, "
               f"ldr={sensor_data.get('ldr')}. "
               f"Light is {light_status}, Fan is {fan_status}.")
    prompt = f"{config.SYSTEM_PROMPT}\n\nContext:\n{context}\n\nUser: {user_text}"

    # Try multiple models until one works
    for model in config.CANDIDATE_MODELS:
        try:
            print(f"[GEMINI] Trying model: {model}")
            r = client.models.generate_content(
                model=model,
                contents=prompt
            )
            response_text = r.text.strip()
            
            # Detect relay commands from user text + AI response
            relay_commands = detect_relay_commands(user_text, response_text)
            if relay_commands:
                print(f"[GEMINI] Detected relay commands: {relay_commands}")
                
            # Cap to MAX_GEMINI_WORDS
            words = response_text.split()
            if len(words) > config.MAX_GEMINI_WORDS:
                response_text = " ".join(words[:config.MAX_GEMINI_WORDS])
                
            print(f"[GEMINI] SUCCESS with model: {model}")
            print(f"[RESPONSE] {response_text}")
            return response_text, relay_commands
            
        except Exception as e:
            print(f"[GEMINI] Model {model} failed: {e}")
            continue  # Try next model

    # All models failed - use fallback response
    print("[GEMINI] All models failed - using fallback response")
    relay_commands = detect_relay_commands(user_text, "")
    return "Kuch gadbad ho gayi", relay_commands
