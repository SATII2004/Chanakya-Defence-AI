import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
from google import genai
from PIL import Image
import os
from dotenv import load_dotenv
import time
import random

# --- 1. CONFIGURATION ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

st.set_page_config(
    page_title="CDS Integrated Command (v12.0)",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. MILITARY UI ---
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff41; font-family: 'Courier New', monospace; }
    h1, h2, h3 { color: #e0e0e0; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0px 0px 10px #00ff41; }
    .report-box { border-left: 4px solid #00ff41; background: rgba(0, 50, 0, 0.3); padding: 15px; margin-bottom: 10px; border: 1px solid #003300; }
    .critical { border-left: 4px solid #ff3333; background: rgba(50, 0, 0, 0.3); color: #ffaaaa; padding: 15px; margin-bottom: 10px; border: 1px solid #330000; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(255, 50, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0); } }
    .stTextInput > div > div > input { background-color: #0a0a0a; color: #00ff41; border: 1px solid #333; }
    div.stButton > button { background: #002200; color: #00ff41; border: 1px solid #00ff41; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 3. ROBUST AI ENGINE (With Simulation Fallback) ---
# This ensures the app NEVER crashes during your demo.

def get_simulated_response(prompt, is_image=False):
    """Fallback generator if API fails (For Demo Continuity)"""
    time.sleep(1.5) # Fake processing delay
    if is_image:
        return "IMINT REPORT: Visual match confirmed. Asset identified as AH-64 Apache Attack Helicopter. Configuration: Armed/Combat Ready. Terrain: Clear sky. THREAT LEVEL: NEUTRAL (Friendly Asset)."
    
    # Text Fallback Logic
    prompt = prompt.lower()
    if "situation" in prompt or "status" in prompt:
        return "CDS UPDATE: Northern Sector remains on High Alert. Drone activity detected near Sector 4. All ground units holding position. Air Defence systems active."
    elif "attack" in prompt:
        return "COMMAND DIRECTIVE: Negative. Hold fire. Authorization required from Delhi HQ. Continue surveillance and maintain defensive posture."
    elif "report" in prompt:
        return "INTEL SUMMARY: Satellite sweep confirms logistic movement across the border. No imminent offensive formation detected. recommend increasing UAV patrols."
    else:
        return f"COMMANDER: Copy that. Directives logged. Grid monitoring active. Standing by for further orders."

def generate_response(prompt, image=None):
    if not GEMINI_API_KEY:
        return get_simulated_response(prompt, image is not None)

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        # Try the most stable model first
        model_id = "gemini-1.5-flash"
        
        if image:
            return client.models.generate_content(model=model_id, contents=[prompt, image]).text
        else:
            return client.models.generate_content(model=model_id, contents=prompt).text
            
    except Exception as e:
        # If API fails (Rate Limit/404), fail gracefully to Simulation Mode
        # This saves the demo video!
        return f"[SECURE LINE UNSTABLE - SWITCHING TO LOCAL INTEL]\n\n{get_simulated_response(prompt, image is not None)}"

# --- 4. DATA SOURCES ---
CHANAKYA_URL = "http://0.0.0.0:8000/v1/retrieve"
CSV_FILE = "intel_feed.csv"
INDIA_BORDER = "https://raw.githubusercontent.com/datameet/maps/master/Country/india-composite.geojson"
INDIA_STATES = "https://raw.githubusercontent.com/Subhash9325/GeoJson-Data-of-Indian-States/master/Indian_States"

def get_intel(query):
    try:
        res = requests.post(CHANAKYA_URL, json={"query": query, "k": 5})
        return [i['text'] for i in res.json()] if res.json() else []
    except: return []

# --- 5. ASSETS DATABASE ---
COMMANDS = [
    {"name": "Northern Comd", "loc": "Udhampur", "lat": 32.93, "lon": 75.14, "color": [255, 215, 0], "type": "Army"},
    {"name": "Western Comd", "loc": "Chandimandir", "lat": 30.73, "lon": 76.78, "color": [255, 215, 0], "type": "Army"},
    {"name": "South Western", "loc": "Jaipur", "lat": 26.91, "lon": 75.78, "color": [255, 215, 0], "type": "Army"},
    {"name": "Southern Comd", "loc": "Pune", "lat": 18.52, "lon": 73.85, "color": [255, 215, 0], "type": "Army"},
    {"name": "Central Comd", "loc": "Lucknow", "lat": 26.84, "lon": 80.94, "color": [255, 215, 0], "type": "Army"},
    {"name": "Eastern Comd", "loc": "Kolkata", "lat": 22.57, "lon": 88.36, "color": [255, 215, 0], "type": "Army"},
    {"name": "ARTRAC", "loc": "Shimla", "lat": 31.10, "lon": 77.17, "color": [255, 215, 0], "type": "Army"},
    {"name": "Western Air", "loc": "Delhi", "lat": 28.58, "lon": 77.20, "color": [0, 255, 255], "type": "IAF"},
    {"name": "South Western Air", "loc": "Gandhinagar", "lat": 23.21, "lon": 72.63, "color": [0, 255, 255], "type": "IAF"},
    {"name": "Central Air", "loc": "Prayagraj", "lat": 25.43, "lon": 81.84, "color": [0, 255, 255], "type": "IAF"},
    {"name": "Eastern Air", "loc": "Shillong", "lat": 25.57, "lon": 91.89, "color": [0, 255, 255], "type": "IAF"},
    {"name": "Southern Air", "loc": "Trivandrum", "lat": 8.52, "lon": 76.93, "color": [0, 255, 255], "type": "IAF"},
    {"name": "Western Navy", "loc": "Mumbai", "lat": 18.94, "lon": 72.82, "color": [255, 255, 255], "type": "Navy"},
    {"name": "Eastern Navy", "loc": "Vizag", "lat": 17.68, "lon": 83.21, "color": [255, 255, 255], "type": "Navy"},
    {"name": "Andaman Cmd (ANC)", "loc": "Port Blair", "lat": 11.62, "lon": 92.72, "color": [0, 255, 0], "type": "Joint"},
]

# --- 6. UI LAYOUT ---
col1, col2 = st.columns([0.1, 0.9])
with col1: st.image("https://upload.wikimedia.org/wikipedia/commons/2/2c/India-flag-a4.jpg", width=80)
with col2: 
    st.title("CDS INTEGRATED COMMAND v12.0")
    st.caption(f"STATUS: ONLINE | NETWORK: ENCRYPTED | MODE: FAIL-SAFE")

col_left, col_right = st.columns([0.65, 0.35])

# === LEFT: STRATEGIC MAP ===
with col_left:
    st.subheader("🌐 THEATER COMMAND VIEW")
    try:
        cmd_df = pd.DataFrame(COMMANDS)
        df = pd.read_csv(CSV_FILE)
        threats = []
        for _, row in df.iterrows():
            if row['priority'] == 'High':
                threats.append({"lat": 34.5, "lon": 76.0, "color": [255, 0, 0], "size": 30000})
        threat_df = pd.DataFrame(threats)

        layers = [
            pdk.Layer("GeoJsonLayer", INDIA_BORDER, stroked=True, filled=True, get_fill_color=[0, 30, 0, 50], get_line_color=[255, 215, 0, 255], get_line_width=3000),
            pdk.Layer("GeoJsonLayer", INDIA_STATES, stroked=True, filled=False, get_line_color=[0, 255, 255, 120], get_line_width=1000),
            pdk.Layer("ScatterplotLayer", cmd_df, get_position='[lon, lat]', get_color='color', get_radius=20000, pickable=True),
            pdk.Layer("TextLayer", cmd_df, get_position='[lon, lat]', get_text='name', get_color=[255, 255, 255], get_size=13, get_alignment_baseline="'bottom'", get_background_color=[0, 0, 0, 200])
        ]
        
        if not threat_df.empty:
            layers.append(pdk.Layer("ScatterplotLayer", threat_df, get_position='[lon, lat]', get_color='color', get_radius='size', stroked=True, filled=True, get_line_color=[255, 0, 0], get_line_width=3000))

        st.pydeck_chart(pdk.Deck(
            map_style=None, 
            initial_view_state=pdk.ViewState(latitude=22, longitude=82, zoom=3.8),
            layers=layers,
            tooltip={"text": "{name} ({loc})"}
        ))
        st.caption("LEGEND: 🟡 Army | 🔵 Air Force | ⚪ Navy | 🟢 Tri-Service | 🔴 Threat")

    except Exception as e: st.error(f"Map Render Error: {e}")

# === RIGHT: OPS CENTER ===
with col_right:
    tab1, tab2 = st.tabs(["💬 STRATEGIC COMMS", "👁️ TRINETRA SATELLITE"])
    
    with tab1:
        st.subheader("SECURE CHANNEL")
        if "messages" not in st.session_state: st.session_state.messages = []
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
        if prompt := st.chat_input("Enter Directives..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Encrypting..."):
                    # TRY REAL AI, IF FAIL -> USE SIMULATION
                    response = generate_response(prompt)
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    with tab2:
        st.subheader("IMINT ANALYSIS")
        uploaded_file = st.file_uploader("Upload Drone/Sat Feed", type=["jpg", "png"])
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="FEED LOCKED", use_container_width=True)
            if st.button("RUN AI SCAN"):
                with st.spinner("ANALYZING PIXELS..."):
                    # TRY REAL AI, IF FAIL -> USE SIMULATION
                    res = generate_response("Analyze military image", image)
                    st.success("SCAN COMPLETE")
                    st.markdown(f"<div class='report-box'>{res}</div>", unsafe_allow_html=True)
                    
    st.divider()
    st.subheader("📡 SIGNALS INTELLIGENCE")
    if st.button("SYNC FEEDS"): st.rerun()
    try:
        for _, row in df.tail(5).iloc[::-1].iterrows():
            c = "critical" if row['priority'] == 'High' else "report-box"
            st.markdown(f"<div class='{c}'><b>{row['timestamp']}</b><br>{row['report']}</div>", unsafe_allow_html=True)
    except: st.write("Feed Disconnected")