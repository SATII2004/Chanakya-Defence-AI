import streamlit as st
import pandas as pd
import requests
import time
import pydeck as pdk  # We use PyDeck for 3D Satellite Maps
from google import genai

# --- CONFIGURATION ---
GEMINI_API_KEY = "AIzaSyAaXdQRCYWeiUw-HklkbmE_F9SsTpFxjGw"
CHANAKYA_URL = "http://0.0.0.0:8000/v1/retrieve"
CSV_FILE = "intel_feed.csv"

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Chanakya Defence Grid (v2.0)",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Military Theme CSS
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff41; font-family: 'Courier New'; }
    .stButton>button { border: 1px solid #00ff41; background-color: #000; color: #00ff41; border-radius: 0px; }
    .stButton>button:hover { background-color: #00ff41; color: #000; }
    .report-box { border-left: 3px solid #00ff41; background: #0a0a0a; padding: 10px; margin-bottom: 10px; }
    .critical { border-left: 3px solid #ff0000; background: #1a0505; color: #ff9999; }
</style>
""", unsafe_allow_html=True)

# --- GEMINI SETUP ---
if "AIza" not in GEMINI_API_KEY:
    st.error("⚠️ CRITICAL: API KEY MISSING.")
    st.stop()

@st.cache_resource
def setup_client():
    return genai.Client(api_key=GEMINI_API_KEY)

client = setup_client()

# --- INTELLIGENCE FUNCTIONS ---
def get_intel_from_chanakya(query):
    try:
        response = requests.post(CHANAKYA_URL, json={"query": query, "k": 5})
        data = response.json()
        if not data: return []
        return [item['text'] for item in data]
    except:
        return []

def ask_commander_strategy(query, context):
    system_prompt = f"""
    You are General Chanakya, Chief Strategist for the Indian Army.
    
    LIVE INTEL: {context}
    USER QUERY: {query}
    
    MISSION: Provide a strategic assessment. 
    TONE: Professional, Decisive, Indian Army protocols. 
    Start with "GENERAL:"
    """
    try:
        # Auto-select best model logic is assumed here or generic fallback
        res = client.models.generate_content(model="gemini-1.5-flash", contents=system_prompt)
        return res.text
    except Exception as e:
        return f"Encrypted Line Failure: {e}"

# --- DYNAMIC GEO-CODING (The "Real World" Magic) ---
# In a real system, we would use an internal Army GIS database.
# For the hackathon, we map key sectors to J&K coordinates.
SECTOR_COORDS = {
    "Northern": [34.5, 76.0],     # General Ladakh/Kargil area
    "Kargil": [34.55, 76.13],
    "Dras": [34.42, 75.76],
    "Uri": [34.08, 74.03],
    "Poonch": [33.77, 74.09],
    "Kupwara": [34.53, 74.25],
    "Siachen": [35.4, 77.1],
    "Galwan": [34.7, 78.2],
    "Sector 4": [34.1, 74.8]      # Placeholder
}

def extract_threat_locations(df):
    """Reads the CSV and creates map points based on keywords."""
    map_points = []
    
    for index, row in df.iterrows():
        text = row['report'] + " " + row['sector']
        lat, lon = 34.08, 74.79 # Default (Srinagar)
        found = False
        
        # Check if any known sector is in the report
        for sector, coords in SECTOR_COORDS.items():
            if sector.lower() in text.lower():
                lat, lon = coords
                found = True
                break
        
        # Color code based on priority
        color = [255, 0, 0, 200] if row['priority'] == 'High' else [0, 255, 65, 200] # Red or Green
        radius = 15000 if row['priority'] == 'High' else 5000
        
        map_points.append({
            "lat": lat, "lon": lon, "type": row['priority'], 
            "color": color, "radius": radius, "info": row['report']
        })
    
    return pd.DataFrame(map_points)

# --- DASHBOARD LAYOUT ---

st.title("🇮🇳 INTEGRATED DEFENCE STAFF: CHANAKYA")
st.caption("CLASSIFIED // EYES ONLY // REAL-TIME SATELLITE LINK")

# Sidebar
with st.sidebar:
    st.header("📡 INTEL STREAM")
    if st.button("RELOAD SATELLITE FEED"):
        st.rerun()
    
    try:
        df = pd.read_csv(CSV_FILE)
        for _, row in df.tail(6).iloc[::-1].iterrows():
            css_class = "critical" if row['priority'] == 'High' else "report-box"
            icon = "🚨" if row['priority'] == 'High' else "🟢"
            st.markdown(f"""
            <div class="{css_class}">
                <b>{icon} {row['timestamp']} | {row['sector']}</b><br>
                {row['report']}
            </div>
            """, unsafe_allow_html=True)
    except:
        st.error("FEED OFFLINE")

# Main Map
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("🛰️ TACTICAL OVERVIEW (J&K SECTOR)")
    
    if 'df' in locals():
        map_df = extract_threat_locations(df)
        
        # 3D Satellite Map Layer
        layer = pdk.Layer(
            "ScatterplotLayer",
            map_df,
            get_position='[lon, lat]',
            get_color='color',
            get_radius='radius',
            pickable=True,
        )

        view_state = pdk.ViewState(
            latitude=34.0, longitude=76.0, zoom=6.5, pitch=45
        )

        # Render Map with Satellite Style
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/satellite-v9', # Satellite view removes political borders
            initial_view_state=view_state,
            layers=[layer],
            tooltip={"text": "{info}"}
        ))
    else:
        st.write("Waiting for data...")

with col2:
    st.subheader("💬 WAR ROOM")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Enter Orders..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Decryption in progress..."):
                intel = get_intel_from_chanakya(prompt)
                intel_str = "\n".join(intel) if intel else "No specific intel."
                response = ask_commander_strategy(prompt, intel_str)
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})