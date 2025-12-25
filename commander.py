from google import genai
import requests
import sys

# --- CONFIGURATION ---
# PASTE YOUR KEY HERE
GEMINI_API_KEY = "AIzaSyAaXdQRCYWeiUw-HklkbmE_F9SsTpFxjGw"

CHANAKYA_URL = "http://0.0.0.0:8000/v1/retrieve"

# --- 1. SETUP CLIENT ---
if "AIza" not in GEMINI_API_KEY:
    print("❌ ERROR: API Key missing. Please paste it in line 7.")
    sys.exit(1)

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Error initializing Client: {e}")
    sys.exit(1)

# --- 2. AUTO-DISCOVER VALID MODELS ---
def get_best_available_model():
    """Asks Google which models this API Key can actually use."""
    print("... Scanning for valid AI models ...")
    try:
        # Get list of all models available to your key
        all_models = list(client.models.list())
        
        # We prefer 'flash' models because they are fast and free-tier friendly
        # We look for models that support 'generateContent'
        valid_models = []
        for m in all_models:
            name = m.name.lower() # e.g. "models/gemini-1.5-flash"
            if "gemini" in name and "vision" not in name:
                valid_models.append(m.name)
        
        # Priority Logic: Flash > Pro > Any other Gemini
        best_model = None
        for m in valid_models:
            if "flash" in m and "exp" not in m: # Stable Flash
                best_model = m
                break
        
        if not best_model and valid_models:
            best_model = valid_models[0] # Fallback to first available
            
        if best_model:
            # The API sometimes wants just the ID, sometimes "models/ID"
            # We strip "models/" to be safe for the new SDK
            clean_name = best_model.replace("models/", "")
            print(f"✅ LOCKED ON MODEL: {clean_name}")
            return clean_name
        else:
            print("❌ CRITICAL: No text-generation models found for this Key.")
            return None

    except Exception as e:
        print(f"❌ Error listing models: {e}")
        # Emergency Fallback if list() fails
        return "gemini-1.5-flash" 

# Set the model ONCE at startup
ACTIVE_MODEL = get_best_available_model()

def get_intel_from_chanakya(query):
    payload = {"query": query, "k": 3} 
    try:
        response = requests.post(CHANAKYA_URL, json=payload)
        data = response.json()
        if not data: return "No intelligence reports found."
        return "\n".join([f"- {item['text']}" for item in data])
    except Exception as e:
        return f"[System Error] Chanakya Offline: {e}"

def ask_commander(user_query, context):
    if not ACTIVE_MODEL:
        return "COMMANDER: SYSTEM FAILURE. AI Model not initialized."

    system_prompt = f"""
    You are Major Chanakya, an AI Strategic Advisor to the Indian Army.
    LIVE INTELLIGENCE: {context}
    USER QUERY: {user_query}
    MISSION: Answer concisely using ONLY the intelligence. Start with "COMMANDER:".
    """

    try:
        response = client.models.generate_content(
            model=ACTIVE_MODEL,
            contents=system_prompt
        )
        return response.text
    except Exception as e:
        return f"COMMANDER: Comms Failure ({e})"

# --- MAIN LOOP ---
if __name__ == "__main__":
    print("\n" + "="*50)
    print(">>> CHANAKYA DEFENCE GRID: ONLINE <<<")
    print("="*50 + "\n")
    
    while True:
        user_input = input("COMMANDER >> ")
        if user_input.lower() in ["exit", "quit"]:
            break
        
        print("\n... Accessing Pathway Feed ...")
        context = get_intel_from_chanakya(user_input)
        
        response = ask_commander(user_input, context)
        
        print("-" * 50)
        print(response)
        print("-" * 50)