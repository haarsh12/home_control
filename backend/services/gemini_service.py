import google.generativeai as genai
import config
import re
import os

# Initialize Gemini client only if API key is available
GEMINI_AVAILABLE = bool(config.GEMINI_API_KEY)

if GEMINI_AVAILABLE:
    try:
        genai.configure(api_key=config.GEMINI_API_KEY, transport="rest")
        print("[GEMINI] Client initialized successfully")
    except Exception as e:
        print(f"[ERROR] [GEMINI] Failed to initialize: {e}")
        GEMINI_AVAILABLE = False
else:
    print("[WARNING] [GEMINI] API key not set - AI responses disabled")

def detect_relay_commands(user_text: str, ai_text: str):
    """Detect relay commands from BOTH user's original STT text AND AI response text"""
    relay_commands = []
    
    # Combine both texts for detection (convert to lowercase for matching)
    combined = (user_text + " " + ai_text).lower()
    
    # Enhanced light detection patterns
    light_on_keywords = [
        # English
        "light on", "turn on light", "switch on light", "light chalu", "light chalao", "light jala",
        # Hindi/Hinglish variations
        "batti on", "batti chalu", "batti jala", "batti chalao",
        "light kar do", "light karo", "light on karo", "light on kar",
        "रोशनी चालू", "बत्ती चालू", "लाइट ऑन",
        # More natural phrases
        "light jala do", "batti jala do", "ujala kar do"
    ]
    
    light_off_keywords = [
        # English  
        "light off", "turn off light", "switch off light", "light band", "light bujha", "light bujhao",
        # Hindi/Hinglish variations
        "batti off", "batti band", "batti bujha", "batti bujhao",
        "light off karo", "light off kar", "light band karo", "light band kar",
        "रोशनी बंद", "बत्ती बंद", "लाइट ऑफ",
        # More natural phrases
        "light bujha do", "batti bujha do", "andhera kar do"
    ]
    
    # Enhanced fan detection patterns
    fan_on_keywords = [
        # English
        "fan on", "turn on fan", "switch on fan", "fan chalu", "fan chalao",
        # Hindi/Hinglish variations  
        "pankha on", "pankha chalu", "pankha chalao", "pankha chala do",
        "fan on karo", "fan chalu karo", "fan kar do",
        "पंखा चालू", "पंखा ऑन", "फैन ऑन",
        # More natural phrases
        "hawa kar do", "thanda kar do"
    ]
    
    fan_off_keywords = [
        # English
        "fan off", "turn off fan", "switch off fan", "fan band", "fan bujha",
        # Hindi/Hinglish variations
        "pankha off", "pankha band", "pankha bujha", "pankha bujha do",
        "fan off karo", "fan band karo", "fan off kar",
        "पंखा बंद", "पंखा ऑफ", "फैन ऑफ",
        # More natural phrases
        "pankha roko", "hawa band kar do"
    ]
    
    # Check for OFF commands first (more specific)
    light_off_detected = any(keyword in combined for keyword in light_off_keywords)
    fan_off_detected = any(keyword in combined for keyword in fan_off_keywords)
    
    # Then check for ON commands
    light_on_detected = any(keyword in combined for keyword in light_on_keywords)
    fan_on_detected = any(keyword in combined for keyword in fan_on_keywords)
    
    # Add commands (OFF takes priority if both detected)
    if light_off_detected:
        relay_commands.append({"device": "light", "state": False})
        print(f"[COMMAND] Light OFF detected in: '{combined[:100]}...'")
    elif light_on_detected:
        relay_commands.append({"device": "light", "state": True})
        print(f"[COMMAND] Light ON detected in: '{combined[:100]}...'")
    
    if fan_off_detected:
        relay_commands.append({"device": "fan", "state": False})
        print(f"[COMMAND] Fan OFF detected in: '{combined[:100]}...'")
    elif fan_on_detected:
        relay_commands.append({"device": "fan", "state": True})
        print(f"[COMMAND] Fan ON detected in: '{combined[:100]}...'")
    
    if relay_commands:
        print(f"[DETECTION] Found {len(relay_commands)} relay commands: {relay_commands}")
    else:
        print(f"[DETECTION] No relay commands found in: '{combined}'")
    
    return relay_commands

def list_available_models():
    """List all available Gemini models for debugging"""
    if not GEMINI_AVAILABLE:
        print("[GEMINI] API not available")
        return []
    
    try:
        models = genai.list_models()
        available_models = []
        print("[GEMINI] Available models:")
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                available_models.append(model.name)
                print(f"  - {model.name}")
        return available_models
    except Exception as e:
        print(f"[ERROR] [GEMINI] Failed to list models: {e}")
        return []

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

    # Comprehensive model list - trying different versions and generations
    candidate_models = [
        # Latest models (try first)
        "models/gemini-1.5-flash-latest",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-flash-001",
        "models/gemini-1.5-flash-002",
        
        # Pro models (more capable but higher quota usage)
        "models/gemini-1.5-pro-latest", 
        "models/gemini-1.5-pro",
        "models/gemini-1.5-pro-001",
        
        # Older stable models (fallback)
        "models/gemini-1.0-pro-latest",
        "models/gemini-1.0-pro",
        "models/gemini-1.0-pro-001",
        
        # Without 'models/' prefix (alternative format)
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash", 
        "gemini-1.5-pro-latest",
        "gemini-1.0-pro-latest",
        "gemini-1.0-pro"
    ]

    last_error = ""
    quota_exhausted_models = []
    
    for model_name in candidate_models:
        try:
            print(f"[GEMINI] Trying model: {model_name}")
            model = genai.GenerativeModel(model_name)
            
            # Configure generation with conservative settings to reduce quota usage
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=100,  # Limit output to save quota
                temperature=0.7,
                top_p=0.8,
                top_k=40
            )
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            response_text = response.text.strip()
            
            # Detect relay commands from user text + AI response
            relay_commands = detect_relay_commands(user_text, response_text)
            if relay_commands:
                print(f"[GEMINI] Detected relay commands: {relay_commands}")
                
            # Cap to MAX_GEMINI_WORDS
            words = response_text.split()
            if len(words) > config.MAX_GEMINI_WORDS:
                response_text = " ".join(words[:config.MAX_GEMINI_WORDS])
                
            print(f"[SUCCESS] Model {model_name} worked!")
            print(f"[RESPONSE] {response_text}")
            return response_text, relay_commands
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] [GEMINI] Model {model_name} failed: {error_msg}")
            last_error = error_msg
            
            # Track quota exhausted models
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                quota_exhausted_models.append(model_name)
                print(f"[INFO] Model {model_name} quota exhausted, trying next...")
                continue
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                print(f"[INFO] Model {model_name} not found, trying next...")
                continue
            elif "403" in error_msg or "PERMISSION_DENIED" in error_msg:
                print(f"[INFO] Model {model_name} permission denied, trying next...")
                continue
            else:
                print(f"[INFO] Model {model_name} failed with: {error_msg}")
                continue

    # Detailed fallback information
    print(f"\n[ERROR] All {len(candidate_models)} Gemini models failed!")
    if quota_exhausted_models:
        print(f"[INFO] Quota exhausted for: {quota_exhausted_models}")
        print("[INFO] Consider upgrading your Gemini API plan or waiting for quota reset")
    print(f"[INFO] Last error: {last_error}")
    
    # Use local command detection as fallback
    relay_commands = detect_relay_commands(user_text, "")
    if relay_commands:
        return "Samajh gaya, command execute kar raha hun", relay_commands
    else:
        return "Kuch gadbad ho gayi, phir se try karo", relay_commands
