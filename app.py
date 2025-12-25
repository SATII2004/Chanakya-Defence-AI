import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
from google import genai
import os
from dotenv import load_dotenv

# --- CONFIGURATION ---
# Load environment variables from .env file
load_dotenv()

# Get API key from environment (NEVER hardcode it!)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Security check
if not GEMINI_API_KEY:
    st.error("⚠️ CRITICAL: GEMINI_API_KEY not found in .env file!")
    st.info("Create a .env file with: GEMINI_API_KEY=your_key_here")
    st.stop()

CHANAKYA_URL = "http://0.0.0.0:8000/v1/retrieve"
CSV_FILE = "intel_feed.csv"

# Official India Map (DataMeet - Survey of India compliant)
INDIA_GEOJSON = "https://raw.githubusercontent.com/datameet/maps/master/Country/india-composite.geojson"

st.set_page_config(page_title="CDS Strategic Command", page_icon="🇮🇳", layout="wide")

# --- MILITARY STYLING ---
st.markdown("""
<style>
    .stApp { background-color: #000500; color: #00ff41; font-family: 'Courier New'; }
    .report-box { border-left: 3px solid #00ff41; background: #001100; padding: 10px; margin-bottom: 5px; }
    .critical { border-left: 3px solid #ff0000; background: #220000; color: #ffaaaa; padding: 10px; margin-bottom: 5px; }
    div.stButton > button { background: #002200; color: #00ff41; border: 1px solid #00ff41; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 1. ROBUST AI SETUP (Auto-Detect Logic Restored) ---
@st.cache_resource
def setup_gemini():
    """Auto-detects the best available Gemini model for your Key."""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        # Scan for available models
        try:
            models = list(client.models.list())
        except Exception:
            return client, "gemini-1.5-flash" # Fallback if list fails

        # Priority: Flash > Pro
        for m in models:
            name = m.name.lower()
            if "flash" in name and "vision" not in name and "8b" not in name:
                # Return the clean name (e.g., "gemini-1.5-flash")
                return client, m.name.replace("models/", "")
        
        return client, "gemini-1.5-flash" # Fallback
    except Exception as e:
        return None, str(e)

client, active_model = setup_gemini()

# --- LOGIC ---
def get_intel(query):
    try:
        res = requests.post(CHANAKYA_URL, json={"query": query, "k": 5})
        return [i['text'] for i in res.json()] if res.json() else []
    except: return []

def ask_cds(query, context):
    prompt = f"ROLE: Chief of Defence Staff (India). INTEL: {context}. QUERY: {query}. ACTION: Strategic Brief."
    try: 
        # Using the auto-detected model
        return client.models.generate_content(model=active_model, contents=prompt).text
    except Exception as e: 
        # This will now show the REAL error message
        return f"⚠️ SECURE LINE ERROR: {e}"

# --- STRATEGIC ASSETS ---
COMMANDS = [
    # ARMY
    {"name": "Northern Comd", "lat": 32.93, "lon": 75.14, "color": [255, 200, 0], "type": "Army"}, 
    {"name": "Western Comd", "lat": 30.73, "lon": 76.78, "color": [255, 200, 0], "type": "Army"},
    {"name": "South Western", "lat": 26.91, "lon": 75.78, "color": [255, 200, 0], "type": "Army"},
    {"name": "Southern Comd", "lat": 18.52, "lon": 73.85, "color": [255, 200, 0], "type": "Army"},
    {"name": "Central Comd", "lat": 26.84, "lon": 80.94, "color": [255, 200, 0], "type": "Army"},
    {"name": "Eastern Comd", "lat": 22.57, "lon": 88.36, "color": [255, 200, 0], "type": "Army"},
    {"name": "Training Comd", "lat": 31.10, "lon": 77.17, "color": [255, 200, 0], "type": "Army"},
    # AIR FORCE
    {"name": "Western Air", "lat": 28.58, "lon": 77.20, "color": [0, 200, 255], "type": "IAF"},
    {"name": "South Western Air", "lat": 23.21, "lon": 72.63, "color": [0, 200, 255], "type": "IAF"},
    {"name": "Central Air", "lat": 25.43, "lon": 81.84, "color": [0, 200, 255], "type": "IAF"},
    {"name": "Eastern Air", "lat": 25.57, "lon": 91.89, "color": [0, 200, 255], "type": "IAF"},
    {"name": "Southern Air", "lat": 8.52, "lon": 76.93, "color": [0, 200, 255], "type": "IAF"},
    {"name": "Maint. Comd", "lat": 21.14, "lon": 79.08, "color": [0, 200, 255], "type": "IAF"},
    {"name": "Training Comd", "lat": 12.97, "lon": 77.59, "color": [0, 200, 255], "type": "IAF"},
    # NAVY
    {"name": "Western Navy", "lat": 18.94, "lon": 72.82, "color": [255, 255, 255], "type": "Navy"},
    {"name": "Eastern Navy", "lat": 17.68, "lon": 83.21, "color": [255, 255, 255], "type": "Navy"},
    {"name": "Southern Navy", "lat": 9.93, "lon": 76.26, "color": [255, 255, 255], "type": "Navy"},
    # TRI-SERVICE
    {"name": "Andaman Cmd (ANC)", "lat": 11.62, "lon": 92.72, "color": [0, 255, 0], "type": "Joint"},
]

# --- UI LAYOUT ---
st.title("🇮🇳 OFFICE OF THE CHIEF OF DEFENCE STAFF")
st.caption(f"INTEGRATED BATTLEFIELD SURVEILLANCE SYSTEM | MODEL: {active_model}")

col_map, col_feed = st.columns([3, 1])

with col_map:
    # 1. READ THREATS
    try:
        df = pd.read_csv(CSV_FILE)
        cmd_df = pd.DataFrame(COMMANDS)
        
        # Create markers for Threats (Red)
        threats = []
        for _, row in df.iterrows():
            if row['priority'] == 'High':
                threats.append({"lat": 34.5, "lon": 76.0, "color": [255, 0, 0], "size": 20000}) 
        threat_df = pd.DataFrame(threats)

        # 2. LAYERS
        layer_border = pdk.Layer(
            "GeoJsonLayer",
            INDIA_GEOJSON,
            stroked=True, filled=True,
            get_fill_color=[0, 50, 0, 30], 
            get_line_color=[255, 215, 0, 200], # Gold Border
            get_line_width=3000
        )

        layer_cmds = pdk.Layer(
            "ScatterplotLayer",
            cmd_df,
            get_position='[lon, lat]',
            get_color='color',
            get_radius=10000,
            pickable=True,
        )
        
        layer_text = pdk.Layer(
            "TextLayer",
            cmd_df,
            get_position='[lon, lat]',
            get_text='name',
            get_color=[200, 255, 200],
            get_size=12,
            get_alignment_baseline="'bottom'"
        )

        layers = [layer_border, layer_cmds, layer_text]
        if not threat_df.empty:
            layer_threats = pdk.Layer(
                "ScatterplotLayer",
                threat_df,
                get_position='[lon, lat]',
                get_color='color',
                get_radius='size',
                stroked=True, filled=True,
                get_line_color=[255, 0, 0],
                get_line_width=2000
            )
            layers.append(layer_threats)

        # 3. RENDER MAP
        st.pydeck_chart(pdk.Deck(
            map_style=None, 
            initial_view_state=pdk.ViewState(latitude=22, longitude=79, zoom=4.5, pitch=0),
            layers=layers,
            tooltip={"text": "{name}"}
        ))
        
        st.caption("🟡 Army | 🔵 Air Force | ⚪ Navy | 🟢 Tri-Service | 🔴 Threat")

    except Exception as e:
        st.error(f"Map Error: {e}")

    # CHAT INTERFACE
    st.subheader("💬 SECURE COMMS")
    if prompt := st.chat_input("Directives?"):
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Encrypting Transmission..."):
                intel = get_intel(prompt)
                resp = ask_cds(prompt, "\n".join(intel))
            st.write(resp)

with col_feed:
    st.subheader("📡 LIVE INTEL")
    if st.button("SYNC"): st.rerun()
    try:
        for _, row in df.tail(6).iloc[::-1].iterrows():
            c = "critical" if row['priority'] == 'High' else "report-box"
            st.markdown(f"<div class='{c}'><b>{row['timestamp']}</b><br>{row['report']}</div>", unsafe_allow_html=True)
    except: st.write("Offline")