import json
import time
import os
import random
from datetime import datetime
from newsapi import NewsApiClient

# --- CONFIGURATION ---
# Get a free key from https://newsapi.org/
NEWS_API_KEY = "YOUR_NEWS_API_KEY"  # <--- REPLACE THIS if you have one
MOCK_MODE = True  # Set to False if you put a real key above

DATA_DIR = "live_data"
STREAM_FILE = os.path.join(DATA_DIR, "intel_stream.jsonl")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def get_real_news():
    try:
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        top_headlines = newsapi.get_top_headlines(q='defense', language='en')
        return [{"text": f"BREAKING: {art['title']} - {art['description']}", "source": "NewsAPI", "time": datetime.now().isoformat()} for art in top_headlines['articles']]
    except:
        return []

def generate_mock_intel():
    locations = ["Ladakh Sector", "Siachen Glacier", "Galwan Valley", "Doklam Plateau", "LOC Poonch", "Indian Ocean Region"]
    events = ["Troop buildup detected", "UAV airspace violation", "Artillery shelling reported", "Cyber attack on comms", "Satellite movement tracked"]
    
    intel = {
        "text": f"ALERT: {random.choice(events)} near {random.choice(locations)}. Severity: {random.choice(['High', 'Critical'])}.",
        "source": "MOCK_SAT_FEED",
        "timestamp": datetime.now().isoformat()
    }
    return intel

print(f"📡 STREAMER STARTED. Writing to {STREAM_FILE}...")

while True:
    new_data = None
    
    if not MOCK_MODE:
        print("Fetching Real News...")
        news = get_real_news()
        if news:
            with open(STREAM_FILE, "a") as f:
                for n in news:
                    f.write(json.dumps(n) + "\n")
            print(f"--> Pushed {len(news)} real articles.")
    
    # Always push one mock event to ensure activity
    mock_event = generate_mock_intel()
    with open(STREAM_FILE, "a") as f:
        f.write(json.dumps(mock_event) + "\n")
    
    print(f"--> [LIVE] New Intel: {mock_event['text']}")
    time.sleep(10)  # Updates every 10 seconds