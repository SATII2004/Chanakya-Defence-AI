import streamlit as st
import pandas as pd
import pydeck as pdk
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
from pypdf import PdfReader
from streamlit_mic_recorder import speech_to_text
from datetime import datetime, timedelta
import random
import plotly.graph_objects as go
import numpy as np
import base64
import edge_tts
import asyncio
from PIL import Image
import requests  # Connects to Pathway Backend

# --- 1. CONFIGURATION ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# CRITICAL FIX: Configure the Google AI Library explicitly
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(
    page_title="C.H.A.N.A.K.Y.A. (v47.0 - Live)",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ASSETS & DATABASE (Local Fallbacks) ---
INTEL_FILE = "intel_feed.csv"
ORDERS_FILE = "command_orders.csv"

def init_dbs():
    if not os.path.exists(INTEL_FILE): 
        pd.DataFrame(columns=["timestamp", "service", "priority", "report", "lat", "lon"]).to_csv(INTEL_FILE, index=False)
    if not os.path.exists(ORDERS_FILE): 
        pd.DataFrame(columns=["timestamp", "id", "target", "order", "status", "reply"]).to_csv(ORDERS_FILE, index=False)

def load_intel(): 
    init_dbs()
    try: 
        df = pd.read_csv(INTEL_FILE, on_bad_lines='skip')
        if 'lat' not in df.columns: df['lat'] = 28.6; df['lon'] = 77.2; df.to_csv(INTEL_FILE, index=False)
        return df
    except: return pd.DataFrame()

def load_orders(): init_dbs(); return pd.read_csv(ORDERS_FILE, on_bad_lines='skip')

def update_order_status(order_id, reply_msg):
    df = load_orders()
    mask = df['id'] == order_id
    if mask.any():
        df.loc[mask, 'status'] = 'EXECUTED'
        df.loc[mask, 'reply'] = reply_msg
        df.to_csv(ORDERS_FILE, index=False)
        return True
    return False

# --- 3. VOICE ENGINE ---
async def generate_audio(text):
    # 'en-IN-PrabhatNeural' is the best for Indian Defence context
    communicate = edge_tts.Communicate(text, "en-IN-PrabhatNeural", rate="-5%", pitch="-15Hz")
    await communicate.save("assets/response.mp3")

def text_to_speech(text):
    try:
        if not os.path.exists("assets"): os.makedirs("assets")
        asyncio.run(generate_audio(text))
        with open("assets/response.mp3", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        uid = int(time.time())
        st.markdown(f"""
            <audio autoplay="true" id="voice-{uid}">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
        """, unsafe_allow_html=True)
    except Exception as e: st.warning(f"Voice Error: {e}")

# --- 4. AI ENGINE (HYBRID: PATHWAY + GEMINI) ---
def generate_response(prompt, image=None, sys_prompt="", speak=False):
    """
    Routes queries to the appropriate engine:
    - Text Queries -> Pathway Live Backend (for RAG)
    - Image Queries -> Direct Gemini API (Computer Vision)
    """
    
    # CASE A: IMAGE ANALYSIS (Uses Direct Gemini)
    if image:
        try:
            if not GEMINI_API_KEY: raise Exception("Offline")
            
            # FIXED: Updated model to 'gemini-2.5-flash'
            model = genai.GenerativeModel("gemini-2.5-flash")
            full_prompt = f"{sys_prompt}\nUSER: {prompt}"
            
            # Pass image and text list
            response = model.generate_content([full_prompt, image])
            response_text = response.text
            
            if speak: text_to_speech(response_text.replace("*", ""))
            return response_text
        except Exception as e: return f"COMMANDER: Optical sensors offline. {e}"

    # CASE B: TEXT/INTEL ANALYSIS (Uses Pathway Backend)
    api_url = "http://localhost:8000/v1/pw_ai_answer"
    
    try:
        # Attempt to hit the Pathway Live Engine
        payload = {"prompt": prompt}
        response = requests.post(api_url, json=payload, timeout=8)
        
        if response.status_code == 200:
            # Parse response (handles direct string or JSON object)
            raw = response.json()
            answer = raw if isinstance(raw, str) else raw.get("result", str(raw))
            
            if speak: text_to_speech(answer.replace("*", ""))
            return answer
        else:
            raise Exception(f"Pathway Status {response.status_code}")

    except Exception as e:
        # FALLBACK: If Pathway is offline, use raw Gemini
        try:
            if not GEMINI_API_KEY: raise Exception("Offline")
            # FIXED: Updated fallback model to 'gemini-2.5-flash'
            model = genai.GenerativeModel("gemini-2.5-flash")
            fallback_resp = model.generate_content(f"{sys_prompt}\nUSER: {prompt}").text
            if speak: text_to_speech(fallback_resp.replace("*", ""))
            return f"[⚠️ BACKEND OFFLINE - USING FALLBACK] {fallback_resp}"
        except:
            return "COMMANDER: All secure lines are down. Check backend connection."

def extract_pdf(f):
    try: return "".join([p.extract_text() for p in PdfReader(f).pages])
    except: return ""

def draw_radar(df_intel):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[0, 100], theta=[0, 0], mode='lines', line=dict(color='#00ff41', width=2)))
    air = df_intel[df_intel['service'].str.contains("AIR", case=False)]
    if not air.empty:
        r_vals, t_vals = [], []
        for _, row in air.tail(5).iterrows():
            try:
                lat_d, lon_d = float(row['lat']) - 28.6, float(row['lon']) - 77.2
                dist = np.sqrt(lat_d**2 + lon_d**2) * 40
                ang = np.degrees(np.arctan2(lon_d, lat_d))
                r_vals.append(min(dist, 95)); t_vals.append(ang if ang > 0 else 360+ang)
            except: pass
        fig.add_trace(go.Scatterpolar(r=r_vals, theta=t_vals, mode='markers', marker=dict(color='#ff0000', size=15, symbol='cross'), name='HOSTILE'))
    
    fig.update_layout(
        template="plotly_dark",
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor='#004400'),
            angularaxis=dict(gridcolor='#004400'),
            bgcolor='rgba(0,0,0,0.5)'
        ),
        showlegend=False,
        height=320,
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20,r=20,t=20,b=20),
        font=dict(color='#00ff41', family="Courier New")
    )
    return fig

# --- 5. OSINT GENERATOR (UI ONLY - Backend handles real streams) ---
def get_osint_feed():
    # This simulates "Intercepted Signals" for the UI visualization
    sources = ["@BorderWatch", "@ConflictIntel", "@KashmirEye", "@DefMinIndia", "@RawIntel", "@GeoPolitix"]
    keywords = ["Troop movement", "Loud bang heard", "Smoke rising", "Convoy spotted", "Jet flyover", "Shelling reported"]
    locations = [{"loc":"Poonch","lat":33.77,"lon":74.09}, {"loc":"Galwan","lat":34.76,"lon":78.22}, {"loc":"Pathankot","lat":32.26,"lon":75.62}, {"loc":"Baramulla","lat":34.19,"lon":74.35}, {"loc":"Doklam","lat":27.29,"lon":88.90}]
    
    feed = []
    for _ in range(6):
        l = random.choice(locations)
        feed.append({
            "Time": (datetime.now() - timedelta(minutes=random.randint(1, 60))).strftime("%H:%M"),
            "Source": random.choice(sources),
            "Intel": f"{random.choice(keywords)} near {l['loc']}. Unverified.",
            "Lat": l['lat'] + random.uniform(-0.05, 0.05),
            "Lon": l['lon'] + random.uniform(-0.05, 0.05),
            "Risk": random.choice(["LOW", "MEDIUM", "HIGH"])
        })
    return pd.DataFrame(feed)

# --- 6. ULTRA-REALISTIC MILITARY UI CSS ---
st.markdown("""
<style>
    /* MAIN THEME */
    .stApp {
        background-color: #020202;
        background-image: 
            radial-gradient(circle at 50% 50%, #051505 0%, #000000 100%);
        color: #00ff41;
        font-family: 'Courier New', monospace;
    }
    
    /* SCANLINES */
    .stApp::before {
        content: " ";
        display: block;
        position: fixed;
        top: 0; left: 0; bottom: 0; right: 0;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        z-index: 2;
        background-size: 100% 2px, 3px 100%;
        pointer-events: none;
    }

    /* HEADER */
    h1 {
        text-transform: uppercase;
        letter-spacing: 4px;
        text-shadow: 0 0 20px #00ff41;
        border-bottom: 2px solid #00ff41;
        padding-bottom: 10px;
        font-weight: 900 !important;
    }
    
    /* GLASS PANELS */
    .glass-box {
        background: rgba(0, 20, 0, 0.6);
        backdrop-filter: blur(8px);
        border: 1px solid #00ff41;
        border-radius: 4px;
        padding: 15px;
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.1);
        margin-bottom: 10px;
    }
    
    /* ALERT BOXES */
    .alert-box {
        background: rgba(0, 10, 0, 0.8);
        border-left: 4px solid #00ff41;
        padding: 10px;
        margin: 5px 0;
        font-family: 'Consolas', monospace;
        font-size: 0.9em;
    }
    .threat-critical {
        border-color: #ff0000;
        background: rgba(40, 0, 0, 0.6);
        box-shadow: inset 0 0 20px rgba(255, 0, 0, 0.2);
        animation: pulse 1s infinite alternate;
    }
    
    /* OSINT CARDS */
    .osint-card {
        background: rgba(0, 30, 60, 0.6);
        border: 1px solid #00d4ff;
        padding: 10px;
        margin-bottom: 8px;
        border-radius: 4px;
        position: relative;
    }
    .osint-card::after {
        content: "UNVERIFIED";
        position: absolute;
        top: 2px; right: 5px;
        font-size: 0.6em;
        color: #00d4ff;
        opacity: 0.7;
    }
    
    /* INPUT FIELDS */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #051005 !important;
        color: #00ff41 !important;
        border: 1px solid #005500 !important;
        border-radius: 0px;
        font-family: 'Courier New', monospace;
    }
    
    /* BUTTONS */
    div.stButton > button {
        background: transparent !important;
        color: #00ff41 !important;
        border: 2px solid #00ff41 !important;
        border-radius: 0px !important;
        text-transform: uppercase;
        font-weight: bold;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background: #00ff41 !important;
        color: #000 !important;
        box-shadow: 0 0 20px #00ff41;
    }
    
    /* TABS */
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        white-space: pre-wrap;
        background-color: rgba(0, 20, 0, 0.5);
        border-radius: 0px;
        color: #00aa00;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(0, 60, 0, 0.8);
        color: #00ff41;
        border-bottom: 2px solid #00ff41;
    }
    
    @keyframes pulse { from { box-shadow: 0 0 5px #ff0000; } to { box-shadow: 0 0 20px #ff0000; } }
</style>
""", unsafe_allow_html=True)

# --- 7. MAP DATA ---
COMMANDS_DATA = [
    {"name":"Northern Comd","lat":32.93,"lon":75.14,"icon":"🛡️","color":[255,215,0]},
    {"name":"Western Comd","lat":30.73,"lon":76.78,"icon":"🛡️","color":[255,215,0]},
    {"name":"South Western","lat":26.91,"lon":75.78,"icon":"🛡️","color":[255,215,0]},
    {"name":"Southern Comd","lat":18.52,"lon":73.85,"icon":"🛡️","color":[255,215,0]},
    {"name":"Central Comd","lat":26.84,"lon":80.94,"icon":"🛡️","color":[255,215,0]},
    {"name":"Eastern Comd","lat":22.57,"lon":88.36,"icon":"🛡️","color":[255,215,0]},
    {"name":"ARTRAC","lat":31.10,"lon":77.17,"icon":"🛡️","color":[255,215,0]},
    {"name":"Western Air","lat":28.58,"lon":77.20,"icon":"✈️","color":[0,255,255]},
    {"name":"South Western Air","lat":23.21,"lon":72.63,"icon":"✈️","color":[0,255,255]},
    {"name":"Central Air","lat":25.43,"lon":81.84,"icon":"✈️","color":[0,255,255]},
    {"name":"Eastern Air","lat":25.57,"lon":91.89,"icon":"✈️","color":[0,255,255]},
    {"name":"Southern Air","lat":8.52,"lon":76.93,"icon":"✈️","color":[0,255,255]},
    {"name":"Western Navy","lat":18.94,"lon":72.82,"icon":"⚓","color":[255,255,255]},
    {"name":"Eastern Navy","lat":17.68,"lon":83.21,"icon":"⚓","color":[255,255,255]},
    {"name":"Southern Navy","lat":9.93,"lon":76.26,"icon":"⚓","color":[255,255,255]},
    {"name":"Andaman Cmd","lat":11.62,"lon":92.72,"icon":"⭐","color":[0,255,0]},
]
INDIA_BORDER = "https://raw.githubusercontent.com/datameet/maps/master/Country/india-composite.geojson"

# --- 8. HEADER UI ---
c1, c2 = st.columns([0.1, 0.9])
with c1: st.image("https://upload.wikimedia.org/wikipedia/commons/2/2c/India-flag-a4.jpg", use_container_width=True)
with c2: 
    st.title("C.H.A.N.A.K.Y.A. DEFENCE SUITE")
    st.caption("PATHWAY STREAMING ENGINE: ACTIVE | DEFCON 4 | SAT-LINK: SECURE")

# --- 9. MAIN LOGIC ---
if "last_msg_count" not in st.session_state: st.session_state.last_msg_count = 0
user_role = st.sidebar.radio("ACCESS LEVEL", ["COMMANDER", "FIELD AGENT"])

# VOICE TOGGLE
st.sidebar.divider()
enable_voice = st.sidebar.checkbox("🔊 JARVIS VOICE", value=True)
if st.sidebar.button("🔓 AUTHENTICATE AUDIO"):
    st.sidebar.success("AUDIO CHANNEL OPEN")

if user_role == "COMMANDER":
    # --- 3D TACTICAL MAP ---
    with st.container():
        df = load_intel()
        threats = []
        if not df.empty and 'lat' in df.columns:
            for _, row in df.iterrows():
                if str(row['priority']).strip() in ["High", "CRITICAL"]:
                    threats.append({"lat": float(row['lat']), "lon": float(row['lon']), "icon": "☠️", "name": "THREAT"})
        
        layers = [
            pdk.Layer("GeoJsonLayer", INDIA_BORDER, filled=True, get_fill_color=[0,20,0,100], get_line_color=[0,255,0], get_line_width=2000),
            pdk.Layer("ScatterplotLayer", pd.DataFrame(COMMANDS_DATA), get_position='[lon, lat]', get_color='color', get_radius=20000, pickable=True),
            pdk.Layer("TextLayer", pd.DataFrame(COMMANDS_DATA), get_position='[lon, lat]', get_text='icon', get_size=30, pickable=True),
            pdk.Layer("TextLayer", pd.DataFrame(COMMANDS_DATA), get_position='[lon, lat]', get_text='name', get_color=[200,200,200], get_size=12, get_pixel_offset=[0, 20])
        ]
        if threats:
            layers.append(pdk.Layer("ScatterplotLayer", pd.DataFrame(threats), get_position='[lon, lat]', get_color=[255, 0, 0], get_radius=35000, pickable=True))
            layers.append(pdk.Layer("TextLayer", pd.DataFrame(threats), get_position='[lon, lat]', get_text='icon', get_size=45, pickable=True))

        st.pydeck_chart(pdk.Deck(initial_view_state=pdk.ViewState(latitude=22, longitude=82, zoom=3.8, pitch=45), layers=layers, height=500, tooltip={"text": "{name}"}))

    # --- OPERATION PANELS ---
    c_main, c_side = st.columns([0.7, 0.3])
    
    with c_main:
        t1, t2, t3, t4, t5, t6 = st.tabs(["💬 COMMS", "⚔️ ORDERS", "📡 RADAR", "📂 VEDA", "👁️ TRINETRA", "🌐 OSINT"])
        
        with t1:
            if "msgs" not in st.session_state: st.session_state.msgs = []
            for m in st.session_state.msgs: st.chat_message(m["role"]).write(m["content"])
            v = speech_to_text(key='v', start_prompt='🎙️ TALK', stop_prompt='⏹️ SEND')
            if p:=st.chat_input("Enter Directives (Queries Pathway Engine)...") or v:
                final = p or v
                st.session_state.msgs.append({"role":"user","content":final})
                st.chat_message("user").write(final)
                with st.chat_message("assistant"):
                    with st.spinner("Connecting to Live RAG Engine..."):
                        # NOW CALLS PATHWAY BACKEND
                        res = generate_response(final, sys_prompt="ROLE: MILITARY COMMANDER.", speak=enable_voice)
                    st.write(res)
                st.session_state.msgs.append({"role":"assistant","content":res})

        with t2:
            st.markdown("##### ⚠️ ISSUE DIRECTIVE")
            col_a, col_b = st.columns([1, 2])
            with col_a:
                target = st.selectbox("Unit", ["ARMY (Northern)", "ARMY (Western)", "NAVY (Western)", "AIR FORCE (Western)"])
                auth = st.text_input("Auth Code", value="X-RAY-99")
            with col_b: order = st.text_area("Order Details", height=100)
            if st.button("🔴 EXECUTE ORDER"):
                if auth == "X-RAY-99" and order:
                    oid = random.randint(1000,9999)
                    pd.DataFrame({"timestamp":[datetime.now().strftime("%H:%M:%S")],"id":[oid],"target":[target],"order":[order],"status":["PENDING"],"reply":["Waiting..."]}).to_csv(ORDERS_FILE, mode='a', header=False, index=False)
                    st.success(f"ORDER #{oid} SENT"); time.sleep(1); st.rerun()
            st.dataframe(load_orders().iloc[::-1], use_container_width=True)

        with t3:
            col_r1, col_r2 = st.columns([2, 1])
            with col_r1: st.plotly_chart(draw_radar(load_intel()), use_container_width=True)
            with col_r2: 
                st.info("RADAR SWEEP ACTIVE")
                if st.button("REFRESH TRACKS"): st.rerun()

        with t4:
            f=st.file_uploader("Upload Brief (PDF)", type='pdf')
            if f: 
                txt=extract_pdf(f)
                if q:=st.chat_input("Ask Veda..."): 
                    st.write(generate_response(q, sys_prompt=f"DOC: {txt[:5000]}", speak=enable_voice))

        with t5:
            st.markdown("##### 🛰️ SATELLITE RECON")
            img_file = st.file_uploader("Upload Feed", type=['png','jpg','jpeg'])
            if img_file:
                image = Image.open(img_file)
                st.image(image, caption="FEED LOCKED", width=400)
                if st.button("ANALYZE TARGET"):
                    with st.spinner("Scanning..."):
                        res = generate_response("Analyze threat level and assets.", image=image, speak=enable_voice)
                        st.markdown(f"<div class='glass-box'>{res}</div>", unsafe_allow_html=True)
        
        # --- FIXED OSINT LAYOUT ---
        with t6:
            c_os1, c_os2 = st.columns([1.2, 1]) 
            
            with c_os1:
                st.markdown("##### 📡 LIVE CHATTER STREAM")
                if st.button("SCAN FREQUENCIES"):
                    st.session_state.osint_cache = get_osint_feed()
                
                if "osint_cache" in st.session_state:
                    for _, row in st.session_state.osint_cache.iterrows():
                        color = "#ff4b4b" if row['Risk'] == "HIGH" else "#00d4ff"
                        st.markdown(f"""
                        <div class='osint-card' style='border-left: 4px solid {color}'>
                            <b style='color:{color}'>{row['Source']}</b> | {row['Time']}<br>
                            {row['Intel']}
                        </div>
                        """, unsafe_allow_html=True)
            
            with c_os2:
                st.markdown("##### 🤖 VERIFY INTEL (PATHWAY)")
                st.markdown("<div class='glass-box'>", unsafe_allow_html=True)
                st.caption("Verifies against the live Pathway News Stream")
                verify_txt = st.text_area("Paste Intercept / Rumor", height=120)
                if st.button("RUN TRUTH CHECK"):
                    with st.spinner("Querying Live Backend..."):
                        check = generate_response(f"Verify this rumor based on the live news stream: {verify_txt}", speak=enable_voice)
                        st.info(check)
                st.markdown("</div>", unsafe_allow_html=True)

    # --- SIDEBAR INTEL FEED ---
    with c_side:
        st.markdown("<div class='glass-box'><h3>⚡ LIVE ALERTS</h3></div>", unsafe_allow_html=True)
        if st.button("SYNC"): st.rerun()
        
        df_intel = load_intel()
        if not df_intel.empty:
            if len(df_intel) > st.session_state.last_msg_count:
                if str(df_intel.iloc[-1]['priority']).strip() == "CRITICAL":
                    sound_url = "https://actions.google.com/sounds/v1/alarms/nuclear_alarm.ogg"
                    if os.path.exists("assets/alarm.mp3"):
                        with open("assets/alarm.mp3", "rb") as f:
                            b64 = base64.b64encode(f.read()).decode()
                            sound_url = f"data:audio/mp3;base64,{b64}"
                    uid = int(time.time())
                    st.markdown(f"""<audio autoplay="true" id="audio-{uid}"><source src="{sound_url}" type="audio/mp3"></audio><script>document.getElementById("audio-{uid}").play();</script>""", unsafe_allow_html=True)
                    st.error("🚨 CRITICAL ALERT")
                st.session_state.last_msg_count = len(df_intel)

            for _, row in df_intel.tail(6).iloc[::-1].iterrows():
                p = str(row['priority']).strip()
                c = "threat-critical" if p=="CRITICAL" else "alert-box"
                st.markdown(f"<div class='{c}'><b>[{row['service']}]</b> {p}<br>{row['report']}</div>", unsafe_allow_html=True)

elif user_role == "FIELD AGENT":
    st.title("📡 FIELD AGENT UPLINK")
    tabs = st.tabs(["🪖 ARMY", "⚓ NAVY", "✈️ AIR FORCE"])
    
    def render_tab(service):
        st.markdown(f"### 📤 {service} REPORT")
        with st.form(key=f"f_{service}"):
            c1, c2, c3 = st.columns([1,1,2])
            prio = c1.select_slider("Threat Level", ["Routine", "High", "CRITICAL"])
            lat = c2.number_input("Lat", value=28.6, format="%.4f")
            lon = c2.number_input("Lon", value=77.2, format="%.4f")
            rep = c3.text_area("Situation Report", height=60)
            if st.form_submit_button("SEND TRAFFIC"):
                pd.DataFrame({"timestamp":[datetime.now().strftime("%H:%M:%S")],"service":[service],"priority":[prio],"report":[rep],"lat":[lat],"lon":[lon]}).to_csv(INTEL_FILE, mode='a', header=False, index=False)
                st.success("SENT"); time.sleep(0.5); st.rerun()
        
        st.divider()
        c_ref, c_head = st.columns([0.2, 0.8])
        with c_ref:
            if st.button("🔄 REFRESH", key=f"ref_{service}"): st.rerun()
        with c_head: st.markdown("### 📥 MISSION ORDERS")
            
        df_o = load_orders()
        my_orders = df_o[df_o['target'].str.contains(service.split()[0], case=False)]
        if not my_orders.empty:
            for _, row in my_orders.iloc[::-1].iterrows():
                s_col = "order-executed" if row['status']=="EXECUTED" else "order-pending"
                st.markdown(f"<div style='border-left:5px solid {'#0f0' if row['status']=='EXECUTED' else '#fc0'}; padding:10px; background:#001100; margin-bottom:5px;'><b>#{row['id']}</b>: {row['order']}<br>STATUS: {row['status']}</div>", unsafe_allow_html=True)
                if row['status'] == "PENDING":
                    reply = st.text_input("Reply", key=f"r_{row['id']}")
                    if st.button("ACKNOWLEDGE", key=f"b_{row['id']}"): update_order_status(row['id'], reply); st.rerun()
        else: st.info("Standby for orders.")

    with tabs[0]: render_tab("ARMY")
    with tabs[1]: render_tab("NAVY")
    with tabs[2]: render_tab("AIR FORCE")