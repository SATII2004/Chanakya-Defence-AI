import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import google.generativeai as genai
from PIL import Image
import os
from dotenv import load_dotenv
import time
from pypdf import PdfReader
from streamlit_mic_recorder import speech_to_text
from datetime import datetime
import random
import plotly.graph_objects as go # FOR RADAR
import numpy as np # FOR RADAR MATH

# --- 1. CONFIGURATION ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

st.set_page_config(
    page_title="CDS Integrated Command (v25.0)",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. UNIVERSAL AI HUNTER ---
valid_model_name = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        all_models = list(genai.list_models())
        my_models = [m.name for m in all_models if 'generateContent' in m.supported_generation_methods]
        for pref in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']:
            if pref in my_models: valid_model_name = pref; break
        if not valid_model_name and my_models: valid_model_name = my_models[0]
    except: pass

# --- 3. DATABASE ---
INTEL_FILE = "intel_feed.csv"
ORDERS_FILE = "command_orders.csv"

def init_dbs():
    if not os.path.exists(INTEL_FILE): pd.DataFrame(columns=["timestamp", "service", "priority", "report"]).to_csv(INTEL_FILE, index=False)
    if not os.path.exists(ORDERS_FILE): pd.DataFrame(columns=["timestamp", "id", "target", "order", "status", "reply"]).to_csv(ORDERS_FILE, index=False)

def load_intel(): init_dbs(); return pd.read_csv(INTEL_FILE, on_bad_lines='skip')
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

# --- 4. STYLING (MILITARY HUD) ---
st.markdown("""
<style>
    .stApp { background-image: linear-gradient(rgba(0,0,0,0.9), rgba(0,0,0,0.9)), url('https://www.transparenttextures.com/patterns/cubes.png'); background-color: #000; color: #0f0; font-family: 'Consolas', monospace; }
    h1, h2, h3 { color: #fff; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 10px #0f0; }
    
    /* RADAR GLOW */
    .radar-container { border: 2px solid #0f0; border-radius: 50%; box-shadow: 0 0 20px #0f0; }
    
    .alert-box { padding: 15px; margin: 10px 0; border-left: 5px solid; background: rgba(0, 30, 0, 0.5); }
    .threat-routine { border-color: #0f0; color: #afa; }
    .threat-critical { border-color: #f00; color: #faa; animation: pulse 1s infinite; }
    
    .order-card { border: 1px solid #004400; padding: 15px; margin-bottom: 10px; border-radius: 5px; background: #001100; }
    .order-pending { border-left: 5px solid #fc0; }
    .order-executed { border-left: 5px solid #0f0; }
    
    @keyframes pulse { 0% { box-shadow: 0 0 0 red; } 50% { box-shadow: 0 0 15px red; } 100% { box-shadow: 0 0 0 red; } }
    
    .stTextInput>div>div>input { background-color: #0a0a0a; color: #0f0; border: 1px solid #333; }
    div.stButton > button { background: #002200; color: #0f0; border: 1px solid #0f0; }
</style>
""", unsafe_allow_html=True)

# --- 5. AI & UTILS ---
def get_simulated_response(prompt, type="general"):
    time.sleep(1)
    if "status" in prompt.lower(): return "CDS UPDATE: Radar sweep active. 3D Terrain analysis complete. Threats identified in Sector 9."
    return "COMMANDER: Directives logged. Grid monitoring active."

def generate_response(prompt, image=None, sys_prompt=""):
    try:
        if not valid_model_name: raise Exception("Offline")
        model = genai.GenerativeModel(valid_model_name)
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        full = f"{sys_prompt}\nUSER: {prompt}"
        return model.generate_content([full, image] if image else full, safety_settings=safety).text
    except: return f"[⚠️ LOCAL NODE] {get_simulated_response(prompt)}"

def extract_pdf(f):
    try: return "".join([p.extract_text() for p in PdfReader(f).pages])
    except: return ""

# --- 6. ASSETS & MAP DATA ---
COMMANDS = [{"name":"Northern Comd","lat":32.93,"lon":75.14,"color":[255,215,0]},{"name":"Western Comd","lat":30.73,"lon":76.78,"color":[255,215,0]},{"name":"South Western","lat":26.91,"lon":75.78,"color":[255,215,0]},{"name":"Southern Comd","lat":18.52,"lon":73.85,"color":[255,215,0]},{"name":"Central Comd","lat":26.84,"lon":80.94,"color":[255,215,0]},{"name":"Eastern Comd","lat":22.57,"lon":88.36,"color":[255,215,0]},{"name":"Western Air","lat":28.58,"lon":77.20,"color":[0,255,255]},{"name":"South Western Air","lat":23.21,"lon":72.63,"color":[0,255,255]},{"name":"Central Air","lat":25.43,"lon":81.84,"color":[0,255,255]},{"name":"Eastern Air","lat":25.57,"lon":91.89,"color":[0,255,255]},{"name":"Southern Air","lat":8.52,"lon":76.93,"color":[0,255,255]},{"name":"Western Navy","lat":18.94,"lon":72.82,"color":[255,255,255]},{"name":"Eastern Navy","lat":17.68,"lon":83.21,"color":[255,255,255]},{"name":"Southern Navy","lat":9.93,"lon":76.26,"color":[255,255,255]},{"name":"Andaman Cmd","lat":11.62,"lon":92.72,"color":[0,255,0]}]
INDIA_BORDER = "https://raw.githubusercontent.com/datameet/maps/master/Country/india-composite.geojson"

# --- 7. RADAR FUNCTION ---
def draw_radar():
    # Simulate Targets
    r = [random.randint(10, 90) for _ in range(5)] # Distances
    theta = [random.randint(0, 360) for _ in range(5)] # Angles
    
    fig = go.Figure()
    
    # 1. Sweep Area
    fig.add_trace(go.Scatterpolar(
        r=[0, 100], theta=[0, 0], mode='lines', line=dict(color='#0f0', width=2), name='Sweep'
    ))
    
    # 2. Targets (Blips)
    fig.add_trace(go.Scatterpolar(
        r=r, theta=theta, mode='markers', marker=dict(color='red', size=10, symbol='cross'), name='Hostiles'
    ))

    fig.update_layout(
        template="plotly_dark",
        polar=dict(radialaxis=dict(visible=True, range=[0, 100]), bgcolor='#001100'),
        showlegend=False,
        height=350,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# --- 8. MAIN LOGIC ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/2/2c/India-flag-a4.jpg", width=100)
    st.header("🔐 AUTHENTICATION")
    user_role = st.radio("Clearance:", ["COMMANDER (CDS)", "FIELD AGENT"], label_visibility="collapsed")
    st.divider()
    
    st.subheader("📡 SIGNALS FEED")
    if st.button("🔄 SYNC"): st.rerun()
    df_intel = load_intel()
    if not df_intel.empty and 'service' in df_intel.columns:
        for _, row in df_intel.tail(5).iloc[::-1].iterrows():
            c = "threat-critical" if row['priority']=="CRITICAL" else "threat-routine"
            st.markdown(f"<div class='alert-box {c}'><b>[{row['service']}] {row['priority']}</b><br><small>{row['timestamp']}</small><br>{row['report']}</div>", unsafe_allow_html=True)

# ==================== FIELD AGENT ====================
if user_role == "FIELD AGENT":
    st.title("📡 FIELD AGENT TERMINAL")
    tabs = st.tabs(["🪖 ARMY", "⚓ NAVY", "✈️ AIR FORCE"])
    
    def render_agent_tab(service_name):
        st.subheader("📤 REPORT TO CDS")
        with st.form(key=f"rep_{service_name}"):
            c1, c2 = st.columns([1,3])
            prio = c1.select_slider("Priority", ["Routine", "High", "CRITICAL"])
            rep = c2.text_area("Intel", height=80)
            if st.form_submit_button("TRANSMIT"):
                pd.DataFrame({"timestamp":[datetime.now().strftime("%H:%M:%S")],"service":[service_name],"priority":[prio],"report":[rep]}).to_csv(INTEL_FILE, mode='a', header=False, index=False)
                st.success("SENT"); time.sleep(0.5); st.rerun()

        st.divider()
        st.subheader("📥 DIRECTIVES")
        df_orders = load_orders()
        service_orders = df_orders[df_orders['target'].str.contains(service_name.split()[0], case=False)]
        
        if not service_orders.empty:
            for _, row in service_orders.iloc[::-1].iterrows():
                status_color = "order-executed" if row['status'] == "EXECUTED" else "order-pending"
                with st.container():
                    st.markdown(f"<div class='order-card {status_color}'><b>ORDER #{row['id']}</b> | {row['timestamp']}<br><big>{row['order']}</big><br><small>STATUS: {row['status']}</small></div>", unsafe_allow_html=True)
                    if row['status'] == "PENDING":
                        reply = st.text_input("Reply", key=f"r_{row['id']}")
                        if st.button("EXECUTE", key=f"b_{row['id']}"):
                            update_order_status(row['id'], reply); st.rerun()
        else: st.info("No active directives.")

    with tabs[0]: render_agent_tab("ARMY")
    with tabs[1]: render_agent_tab("NAVY")
    with tabs[2]: render_agent_tab("AIR FORCE")
    st.stop()

# ==================== COMMANDER ====================
st.title("🇮🇳 CDS INTEGRATED COMMAND")
st.caption(f"AI STATUS: {'🟢 ONLINE' if valid_model_name else '🟠 LOCAL'} | 3D TERRAIN: ACTIVE")

# 3D MAP LOGIC
with st.container():
    try:
        df = load_intel()
        threats = []
        if not df.empty and 'priority' in df.columns:
            for _, row in df.iterrows():
                if row['priority'] in ["High", "CRITICAL"]:
                    lat, lon = 34.5, 76.0
                    if "sector 9" in str(row['report']).lower(): lat, lon = 28.6, 70.0
                    color = [255,0,0, 200] if row['priority']=="CRITICAL" else [255,140,0, 200]
                    threats.append({"lat":lat, "lon":lon, "color":color, "radius":40000, "height": 80000}) # Height for 3D

        # 3D LAYERS
        layers = [
            pdk.Layer("GeoJsonLayer", INDIA_BORDER, filled=True, get_fill_color=[0,40,0,80], get_line_color=[255,215,0], get_line_width=2000),
            # Command Bases as GOLD PILLARS
            pdk.Layer("ColumnLayer", pd.DataFrame(COMMANDS), get_position='[lon,lat]', get_fill_color='color', radius=20000, elevation_scale=100, get_elevation=500, pickable=True, extruded=True),
            pdk.Layer("TextLayer", pd.DataFrame(COMMANDS), get_position='[lon,lat]', get_text='name', get_color=[255,255,255], get_size=12, get_alignment_baseline="'top'")
        ]
        # Threats as RED SPIKES
        if threats: 
            layers.append(pdk.Layer("ColumnLayer", pd.DataFrame(threats), get_position='[lon,lat]', get_fill_color='color', radius=15000, elevation_scale=100, get_elevation='height', extruded=True))

        # 3D VIEW STATE (PITCHED)
        view_state = pdk.ViewState(latitude=22, longitude=82, zoom=4, pitch=50) # Pitch creates 3D effect
        
        st.pydeck_chart(pdk.Deck(initial_view_state=view_state, layers=layers, height=500))
    except: st.error("Map Offline")

t1, t2, t3, t4, t5 = st.tabs(["💬 COMMS", "⚔️ C2 WING", "📡 RADAR", "📂 VEDA", "👁️ TRINETRA"])

with t1:
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs: st.chat_message(m["role"]).write(m["content"])
    c1,c2=st.columns([1,8]); v=speech_to_text(key='v', start_prompt='🎙️', stop_prompt='⏹️')
    if p:=st.chat_input("Directives...") or v:
        final = p or v
        st.session_state.msgs.append({"role":"user","content":final})
        st.chat_message("user").write(final)
        with st.chat_message("assistant"):
            intel="\n".join([f"{r['service']}: {r['report']}" for _,r in load_intel().tail(5).iterrows()])
            res = generate_response(final, sys_prompt=f"ROLE: CDS. INTEL: {intel}. ORDERS: {load_orders().tail(3).to_string()}.")
            st.write(res)
        st.session_state.msgs.append({"role":"assistant","content":res})

with t2:
    st.subheader("⚠️ COMMAND TRANSMISSION")
    c1, c2 = st.columns([1, 2])
    with c1:
        target = st.selectbox("Target Unit", ["ARMY (Northern Comd)", "ARMY (Western Comd)", "NAVY (Western Fleet)", "AIR FORCE (Western Cmd)"])
        auth = st.text_input("Auth Code", placeholder="X-RAY-99")
    with c2: order = st.text_area("Operational Order", height=100)
    
    if st.button("🔴 TRANSMIT"):
        if auth == "X-RAY-99" and order:
            oid = random.randint(1000,9999)
            pd.DataFrame({"timestamp":[datetime.now().strftime("%H:%M:%S")],"id":[oid],"target":[target],"order":[order],"status":["PENDING"],"reply":["Waiting..."]}).to_csv(ORDERS_FILE, mode='a', header=False, index=False)
            st.success(f"ORDER #{oid} SENT"); time.sleep(1); st.rerun()
    
    st.divider()
    st.subheader("🗂️ LOGS")
    df_o = load_orders()
    if not df_o.empty: st.dataframe(df_o.iloc[::-1], use_container_width=True)

with t3:
    st.subheader("AEW&C RADAR FEED")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("### SECTOR 9 SCAN")
        st.plotly_chart(draw_radar(), use_container_width=True)
    with c2:
        st.write("**DETECTED SIGNATURES:**")
        st.warning("⚠️ UNIDENTIFIED AIRCRAFT (Bearing 045, Dist 40km)")
        st.info("ℹ️ FRIENDLY SU-30 MKI (Bearing 180, Dist 20km)")
        if st.button("REFRESH SCAN"): st.rerun()

with t4:
    f=st.file_uploader("Upload Brief", type='pdf')
    if f: 
        txt=extract_pdf(f)
        if q:=st.chat_input("Query"): st.write(generate_response(q, sys_prompt=f"DOC: {txt[:5000]}"))

with t5:
    i=st.file_uploader("Upload Feed", type=['png','jpg'])
    if i and st.button("SCAN"): st.write(generate_response("Analyze threat", image=Image.open(i)))