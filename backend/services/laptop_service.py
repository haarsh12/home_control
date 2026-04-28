"""
Laptop Command Service
Handles parsing voice commands and translating Hindi to English for laptop control
"""

from google import genai
import config
import re
from typing import Dict, Any, Optional, Tuple

# Initialize Gemini client
GEMINI_AVAILABLE = bool(config.GEMINI_API_KEY)
client = None

if GEMINI_AVAILABLE:
    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        print("[LAPTOP_SERVICE] Gemini client initialized")
    except Exception as e:
        print(f"[ERROR] [LAPTOP_SERVICE] Failed to initialize Gemini: {e}")
        GEMINI_AVAILABLE = False


def parse_laptop_command(user_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse user voice command (English or Hindi) into laptop action
    
    Args:
        user_text: User's voice command (can be Hindi or English)
        
    Returns:
        Dict with action and parameters, or None if not a laptop command
    """
    
    if not GEMINI_AVAILABLE:
        print("[LAPTOP_SERVICE] Gemini not available, using fallback parser")
        return _fallback_parse(user_text)
    
    # Use Gemini to parse and translate
    prompt = f"""You are a voice command parser for laptop control. Parse the following command and return ONLY a JSON object.

User said: "{user_text}"

Your task:
1. Detect if this is a laptop control command (YouTube, Google search, open app, open website, etc.)
2. If it's in Hindi/Hinglish, translate to English
3. Extract the action and parameters

Return ONLY valid JSON in this format:
{{"action": "open_youtube", "query": "song name"}}
{{"action": "google_search", "query": "search term"}}
{{"action": "open_url", "url": "website.com"}}
{{"action": "open_app", "app": "app name"}}
{{"action": "none"}}

Common Hindi/Hinglish patterns:
- "youtube pe X bajao" / "youtube par X play karo" → {{"action": "open_youtube", "query": "X"}}
- "google pe X search karo" → {{"action": "google_search", "query": "X"}}
- "X website kholo" → {{"action": "open_url", "url": "X"}}
- "X app kholo" → {{"action": "open_app", "app": "X"}}

Examples:
- "youtube pe chamak challo bajao" → {{"action": "open_youtube", "query": "chamak challo"}}
- "play saibo song" → {{"action": "open_youtube", "query": "saibo"}}
- "google pe weather search karo" → {{"action": "google_search", "query": "weather"}}
- "spotify kholo" → {{"action": "open_app", "app": "spotify"}}
- "light on karo" → {{"action": "none"}} (not a laptop command)

Return ONLY the JSON, no explanation."""

    try:
        response = client.models.generate_content(
            model=config.CANDIDATE_MODELS[0],
            contents=prompt
        )
        
        response_text = response.text.strip()
        print(f"[LAPTOP_SERVICE] Gemini response: {response_text}")
        
        # Extract JSON from response
        import json
        
        # Try to find JSON in the response
        json_match = re.search(r'\{[^}]+\}', response_text)
        if json_match:
            command = json.loads(json_match.group())
            
            # Check if it's a valid laptop command
            if command.get("action") == "none":
                return None
            
            if command.get("action") in ["open_youtube", "google_search", "open_url", "open_app", "play_music"]:
                print(f"[LAPTOP_SERVICE] Parsed command: {command}")
                return command
        
        return None
        
    except Exception as e:
        print(f"[ERROR] [LAPTOP_SERVICE] Gemini parsing failed: {e}")
        return _fallback_parse(user_text)


def _fallback_parse(user_text: str) -> Optional[Dict[str, Any]]:
    """Fallback parser using regex patterns"""
    
    text_lower = user_text.lower()
    
    # YouTube patterns (English + Hindi/Hinglish)
    youtube_patterns = [
        r'(?:youtube\s+(?:pe|par|mein|me)\s+)?(.+?)\s+(?:bajao|play\s+karo|chalao)',
        r'(?:play|bajao)\s+(.+?)\s+(?:on\s+)?(?:youtube|yt)',
        r'youtube\s+(?:pe|par|open\s+karke)\s+(.+)',
        r'play\s+(.+)',
    ]
    
    for pattern in youtube_patterns:
        match = re.search(pattern, text_lower)
        if match:
            query = match.group(1).strip()
            # Remove common filler words
            query = re.sub(r'\b(song|video|music|gaana|gana)\b', '', query).strip()
            if query:
                return {"action": "open_youtube", "query": query}
    
    # Google search patterns
    google_patterns = [
        r'google\s+(?:pe|par|mein|me)\s+(.+?)\s+(?:search\s+karo|dhundo)',
        r'(?:search|dhundo)\s+(.+?)\s+(?:on\s+)?google',
        r'google\s+(.+)',
    ]
    
    for pattern in google_patterns:
        match = re.search(pattern, text_lower)
        if match:
            query = match.group(1).strip()
            return {"action": "google_search", "query": query}
    
    # App open patterns
    app_patterns = [
        r'(.+?)\s+(?:app\s+)?(?:kholo|open\s+karo|chalu\s+karo)',
        r'(?:open|launch|start)\s+(.+)',
    ]
    
    for pattern in app_patterns:
        match = re.search(pattern, text_lower)
        if match:
            app = match.group(1).strip()
            if app not in ['youtube', 'google']:
                return {"action": "open_app", "app": app}
    
    # Website patterns
    if 'website' in text_lower or '.com' in text_lower or '.in' in text_lower:
        # Extract website name
        match = re.search(r'(.+?)\s+website', text_lower)
        if match:
            site = match.group(1).strip()
            return {"action": "open_url", "url": f"https://www.google.com/search?q={site}"}
    
    return None


def translate_hindi_to_english(text: str) -> str:
    """
    Translate Hindi/Hinglish text to English using Gemini
    
    Args:
        text: Hindi or Hinglish text
        
    Returns:
        English translation
    """
    
    if not GEMINI_AVAILABLE:
        return text
    
    prompt = f"""Translate this Hindi/Hinglish text to English. Return ONLY the English translation, nothing else.

Text: "{text}"

Translation:"""

    try:
        response = client.models.generate_content(
            model=config.CANDIDATE_MODELS[0],
            contents=prompt
        )
        
        translation = response.text.strip()
        print(f"[LAPTOP_SERVICE] Translated '{text}' → '{translation}'")
        return translation
        
    except Exception as e:
        print(f"[ERROR] [LAPTOP_SERVICE] Translation failed: {e}")
        return text


def is_laptop_command(user_text: str) -> bool:
    """
    Quick check if text is likely a laptop command
    
    Args:
        user_text: User's voice command
        
    Returns:
        True if likely a laptop command
    """
    
    text_lower = user_text.lower()
    
    # Keywords that indicate laptop commands
    laptop_keywords = [
        'youtube', 'yt', 'play', 'bajao', 'chalao',
        'google', 'search', 'dhundo',
        'website', 'kholo', 'open',
        'app', 'spotify', 'chrome', 'firefox',
        '.com', '.in', '.org',
    ]
    
    return any(keyword in text_lower for keyword in laptop_keywords)
