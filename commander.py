from google import genai
import requests
import sys

# --- CONFIGURATION ---
# PASTE YOUR KEY INSIDE THE QUOTES BELOW
GEMINI_API_KEY = "AIzaSyBifE-kpqARHpIVAKK_bzCk-DmkU4NAY8Y" 

# This is where Chanakya (your other script) lives
CHANAKYA_URL = "http://0.0.0.0:8000/v1/retrieve"

# --- SETUP GEMINI (NEW LIBRARY) ---
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Error initializing Gemini Client: {e}")
    sys.exit(1)

def get_intel_from_chanakya(query):
    """Asks Pathway (Chanakya) for the latest real-time data."""
    # We ask for the top 3 most relevant reports (k=3)
    payload = {"query": query, "k": 3} 
    try:
        response = requests.post(CHANAKYA_URL, json=payload)
        data = response.json()
        
        if not data:
            return "No relevant intel found in the feed."
            
        # Combine all retrieved reports into one text block
        context = "\n".join([f"- {item['text']}" for item in data])
        return context
    except Exception as e:
        return f"Error connecting to Chanakya Server: {e}"

def ask_commander(user_query):
    # 1. Get Real-Time Context from Chanakya
    intel_context = get_intel_from_chanakya(user_query)
    
    # 2. Design the Military Prompt (The "Personality")
    system_prompt = f"""
    You are Major Chanakya, an AI Strategic Advisor to the Indian Army.
    
    VERIFIED LIVE INTELLIGENCE FROM FIELD:
    {intel_context}
    
    USER QUERY: {user_query}
    
    MISSION: Answer the user's query using ONLY the Verified Live Intelligence above. 
    STYLE: Military, Brevity, Precise. Start with "COMMANDER:". 
    If the intel shows a 'CRITICAL' or 'High' priority threat, use uppercase for the warning.
    """

    # 3. Get Answer from Gemini
    try:
        # We use the new 'gemini-1.5-flash' model which is fast and free
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=system_prompt
        )
        return response.text
    except Exception as e:
        return f"Comms Link Failure (Gemini Error): {e}"

# --- MAIN LOOP ---
if __name__ == "__main__":
    print("\n" + "="*40)
    print(">>> CHANAKYA DEFENCE GRID: ONLINE <<<")
    print("="*40 + "\n")
    print("Type 'exit' to close connection.\n")
    
    while True:
        user_input = input("COMMANDER >> ")
        if user_input.lower() in ["exit", "quit"]:
            print("Link Terminated.")
            break
        
        print("\n... Establishing Secure Link ...\n")
        response = ask_commander(user_input)
        print(response)
        print("-" * 50)