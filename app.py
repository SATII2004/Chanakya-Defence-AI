import streamlit as st
import pandas as pd
import pydeck as pdk
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
from pypdf import PdfReader
from streamlit_mic_recorder import speech_to_text
from datetime import datetime
import random
import plotly.graph_objects as go
import numpy as np
import base64

# --- 1. CONFIGURATION ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

st.set_page_config(
    page_title="CDS Integrated Command (v39.0)",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ASSETS & DATABASE ---
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

# --- 3. AI ENGINE ---
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

def generate_response(prompt, image=None, sys_prompt=""):
    try:
        if not valid_model_name: raise Exception("Offline")
        model = genai.GenerativeModel(valid_model_name)
        full = f"{sys_prompt}\nUSER: {prompt}"
        return model.generate_content([full, image] if image else full).text
    except: return "COMMANDER: Secure line unstable. Using local analysis."

def extract_pdf(f):
    try: return "".join([p.extract_text() for p in PdfReader(f).pages])
    except: return ""

def draw_radar(df_intel):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[0, 100], theta=[0, 0], mode='lines', line=dict(color='#0f0', width=2)))
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
        fig.add_trace(go.Scatterpolar(r=r_vals, theta=t_vals, mode='markers', marker=dict(color='red', size=18, symbol='x')))
    fig.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=True, range=[0, 100]), bgcolor='rgba(0,20,0,0.8)'), showlegend=False, height=350, paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20,r=20,t=20,b=20))
    return fig

# --- 4. STYLING ---
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(rgba(0, 10, 0, 0.9), rgba(0, 10, 0, 0.8)), 
                    url('https://www.transparenttextures.com/patterns/carbon-fibre.png');
        background-color: #050505;
        color: #e0f0e0;
        font-family: 'Segoe UI', 'Roboto', monospace;
    }
    .stApp::before {
        content: " "; display: block; position: fixed; top: 0; left: 0; bottom: 0; right: 0;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        z-index: 2; background-size: 100% 2px, 3px 100%; pointer-events: none;
    }
    h1 { text-shadow: 0 0 15px #00ff41; font-weight: 800 !important; letter-spacing: 3px; border-bottom: 2px solid #004400; padding-bottom: 10px; }
    .glass-box { background: rgba(0, 40, 0, 0.4); backdrop-filter: blur(10px); border: 1px solid rgba(0, 255, 65, 0.2); padding: 15px; border-radius: 8px; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5); }
    .alert-box { padding: 12px; margin: 8px 0; border-left: 6px solid; font-family: monospace; background: rgba(0,0,0,0.6); }
    .threat-routine { border-color: #00ff41; color: #aaffaa; }
    .threat-critical { border-color: #ff0000; color: #ffaaaa; background: rgba(50, 0, 0, 0.6); animation: pulse 1s infinite alternate; box-shadow: 0 0 20px rgba(255, 0, 0, 0.2); }
    @keyframes pulse { from { box-shadow: 0 0 5px #ff0000; } to { box-shadow: 0 0 20px #ff0000; } }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea { background-color: rgba(0, 20, 0, 0.8) !important; color: #00ff41 !important; border: 1px solid #004400 !important; }
    div.stButton > button { background: linear-gradient(45deg, #002200, #004400) !important; color: #00ff41 !important; border: 1px solid #00ff41 !important; font-weight: bold; transition: all 0.3s; }
    div.stButton > button:hover { box-shadow: 0 0 15px #00ff41; transform: scale(1.02); }
</style>
""", unsafe_allow_html=True)

# --- 5. MAP DATA ---
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

# --- 6. HEADER ---
c1, c2 = st.columns([0.15, 0.85])
with c1: st.image("https://upload.wikimedia.org/wikipedia/commons/2/2c/India-flag-a4.jpg", use_container_width=True)
with c2: st.title("🇮🇳 CDS INTEGRATED DEFENCE STAFF"); st.caption("NETWORK: ENCRYPTED (AES-256) | DEFCON: 4 | SAT-LINK: ACTIVE")

# --- 7. MAIN LOGIC ---
if "last_msg_count" not in st.session_state: st.session_state.last_msg_count = 0
user_role = st.sidebar.radio("Clearance Level", ["COMMANDER (CDS)", "FIELD AGENT"])

# --- AUDIO UNLOCKER BUTTON (ESSENTIAL FOR BROWSER POLICY) ---
st.sidebar.divider()
if st.sidebar.button("🔊 INITIALIZE AUDIO SYSTEM"):
    st.sidebar.success("AUDIO LINK ESTABLISHED")

if user_role == "COMMANDER (CDS)":
    with st.container():
        df = load_intel()
        threats = []
        if not df.empty and 'lat' in df.columns:
            for _, row in df.iterrows():
                if str(row['priority']).strip() in ["High", "CRITICAL"]:
                    threats.append({"lat": float(row['lat']), "lon": float(row['lon']), "icon": "☠️", "name": "THREAT"})
        
        layers = [
            pdk.Layer("GeoJsonLayer", INDIA_BORDER, filled=True, get_fill_color=[0,30,0,80], get_line_color=[255,215,0], get_line_width=2000),
            pdk.Layer("ScatterplotLayer", pd.DataFrame(COMMANDS_DATA), get_position='[lon, lat]', get_color='color', get_radius=25000, pickable=True),
            pdk.Layer("TextLayer", pd.DataFrame(COMMANDS_DATA), get_position='[lon, lat]', get_text='icon', get_size=35, pickable=True),
            pdk.Layer("TextLayer", pd.DataFrame(COMMANDS_DATA), get_position='[lon, lat]', get_text='name', get_color=[200,200,200], get_size=11, get_pixel_offset=[0, 20])
        ]
        if threats:
            layers.append(pdk.Layer("ScatterplotLayer", pd.DataFrame(threats), get_position='[lon, lat]', get_color=[255, 0, 0], get_radius=40000, pickable=True))
            layers.append(pdk.Layer("TextLayer", pd.DataFrame(threats), get_position='[lon, lat]', get_text='icon', get_size=50, pickable=True))

        st.pydeck_chart(pdk.Deck(initial_view_state=pdk.ViewState(latitude=22, longitude=82, zoom=3.8, pitch=45), layers=layers, height=550, tooltip={"text": "{name}"}))

    c1, c2 = st.columns([0.65, 0.35])
    with c1:
        t1, t2, t3, t4, t5 = st.tabs(["💬 COMMS", "⚔️ C2 WING", "📡 RADAR", "📂 VEDA", "👁️ TRINETRA"])
        
        with t1:
            if "msgs" not in st.session_state: st.session_state.msgs = []
            for m in st.session_state.msgs: st.chat_message(m["role"]).write(m["content"])
            v = speech_to_text(key='v', start_prompt='🎙️ PTT', stop_prompt='⏹️ SEND')
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
            st.markdown("### ⚠️ ISSUE OPERATIONAL ORDERS")
            col_a, col_b = st.columns([1, 2])
            with col_a:
                target = st.selectbox("Target Unit", ["ARMY (Northern)", "ARMY (Western)", "NAVY (Western)", "AIR FORCE (Western)"])
                auth = st.text_input("Auth Code", value="X-RAY-99")
            with col_b: order = st.text_area("Order Directive", height=100)
            if st.button("🔴 TRANSMIT ORDER"):
                if auth == "X-RAY-99" and order:
                    oid = random.randint(1000,9999)
                    pd.DataFrame({"timestamp":[datetime.now().strftime("%H:%M:%S")],"id":[oid],"target":[target],"order":[order],"status":["PENDING"],"reply":["Waiting..."]}).to_csv(ORDERS_FILE, mode='a', header=False, index=False)
                    st.success(f"ORDER #{oid} TRANSMITTED"); time.sleep(1); st.rerun()
            st.divider()
            df_o = load_orders()
            if not df_o.empty: st.dataframe(df_o.iloc[::-1], use_container_width=True)

        with t3:
            col_r1, col_r2 = st.columns([2, 1])
            with col_r1: st.plotly_chart(draw_radar(load_intel()), use_container_width=True)
            with col_r2: 
                if st.button("REFRESH SWEEP"): st.rerun()
                st.caption("Real-time tracks from IAF Uplink.")

        with t4:
            f=st.file_uploader("Upload Brief", type='pdf')
            if f: 
                txt=extract_pdf(f)
                if q:=st.chat_input("Query Document"): st.write(generate_response(q, sys_prompt=f"DOC: {txt[:5000]}"))

        with t5:
            st.markdown("### 🛰️ SATELLITE IMAGERY ANALYSIS")
            img_file = st.file_uploader("Upload Drone/Sat Feed", type=['png','jpg','jpeg'])
            if img_file:
                image = Image.open(img_file)
                st.image(image, caption="TARGET LOCKED", width=400)
                if st.button("RUN TRINETRA AI SCAN"):
                    with st.spinner("Analyzing spectral signature..."):
                        res = generate_response("Analyze this military image. Identify assets, threats, and terrain.", image=image)
                        st.success("SCAN COMPLETE")
                        st.markdown(f"<div class='alert-box threat-high'>{res}</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='glass-box'><h3>📡 SIGNALS INTEL</h3></div>", unsafe_allow_html=True)
        if st.button("🔄 SYNC FEED"): st.rerun()
        
        df_intel = load_intel()
        if not df_intel.empty:
            current_count = len(df_intel)
            last_row = df_intel.iloc[-1]
            prio = str(last_row['priority']).strip()
            
            # --- AGGRESSIVE AUDIO INJECTION WITH VISUAL TRIGGER ---
            if current_count > st.session_state.last_msg_count:
                if prio == "CRITICAL":
                    # Load Sound
                    sound_url = "https://actions.google.com/sounds/v1/alarms/nuclear_alarm.ogg"
                    if os.path.exists("assets/alarm.mp3"):
                        with open("assets/alarm.mp3", "rb") as f:
                            b64 = base64.b64encode(f.read()).decode()
                            sound_url = f"data:audio/mp3;base64,{b64}"

                    # Unique ID to force new audio element
                    unique_id = int(time.time())
                    
                    # INJECT AUDIO
                    st.markdown(f"""
                        <audio autoplay="true" id="audio-{unique_id}">
                            <source src="{sound_url}" type="audio/mp3">
                        </audio>
                        <script>
                            var audio = document.getElementById("audio-{unique_id}");
                            audio.play().catch(function(error) {{
                                console.log("Audio play failed: " + error);
                            }});
                        </script>
                    """, unsafe_allow_html=True)
                    
                    st.error("🚨 CRITICAL ALERT RECEIVED")
                st.session_state.last_msg_count = current_count

            for _, row in df_intel.tail(6).iloc[::-1].iterrows():
                p = str(row['priority']).strip()
                c = "threat-critical" if p=="CRITICAL" else "threat-routine"
                st.markdown(f"<div class='alert-box {c}'><b>[{row['service']}]</b> {p}<br>{row['report']}</div>", unsafe_allow_html=True)

elif user_role == "FIELD AGENT":
    st.title("📡 FIELD AGENT TERMINAL")
    tabs = st.tabs(["🪖 ARMY", "⚓ NAVY", "✈️ AIR FORCE"])
    
    def render_tab(service):
        st.markdown(f"### 📤 {service} UPLINK")
        with st.form(key=f"f_{service}"):
            c1, c2, c3 = st.columns([1,1,2])
            prio = c1.select_slider("Priority", ["Routine", "High", "CRITICAL"])
            lat = c2.number_input("Lat", value=28.6, format="%.4f")
            lon = c2.number_input("Lon", value=77.2, format="%.4f")
            rep = c3.text_area("Intel Detail", height=60)
            if st.form_submit_button("TRANSMIT"):
                pd.DataFrame({"timestamp":[datetime.now().strftime("%H:%M:%S")],"service":[service],"priority":[prio],"report":[rep],"lat":[lat],"lon":[lon]}).to_csv(INTEL_FILE, mode='a', header=False, index=False)
                st.success("TRANSMISSION COMPLETE"); time.sleep(0.5); st.rerun()
        
        st.divider()
        c_ref, c_head = st.columns([0.2, 0.8])
        with c_ref:
            if st.button("🔄 REFRESH ORDERS", key=f"ref_{service}"): st.rerun()
        with c_head:
            st.markdown("### 📥 COMMAND ORDERS")
            
        df_o = load_orders()
        my_orders = df_o[df_o['target'].str.contains(service.split()[0], case=False)]
        if not my_orders.empty:
            for _, row in my_orders.iloc[::-1].iterrows():
                s_col = "order-executed" if row['status']=="EXECUTED" else "order-pending"
                st.markdown(f"<div style='border-left:5px solid {'#0f0' if row['status']=='EXECUTED' else '#fc0'}; padding:10px; background:#001100; margin-bottom:5px;'><b>#{row['id']}</b>: {row['order']}<br>STATUS: {row['status']}</div>", unsafe_allow_html=True)
                if row['status'] == "PENDING":
                    reply = st.text_input("Reply", key=f"r_{row['id']}")
                    if st.button("EXECUTE", key=f"b_{row['id']}"): update_order_status(row['id'], reply); st.rerun()
        else: st.info("No active directives.")

    with tabs[0]: render_tab("ARMY")
    with tabs[1]: render_tab("NAVY")
    with tabs[2]: render_tab("AIR FORCE")