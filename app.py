import streamlit as st
import pandas as pd
import requests
import time
from google import genai

# --- CONFIGURATION ---
# PASTE YOUR KEY HERE
GEMINI_API_KEY = "AIzaSyAaXdQRCYWeiUw-HklkbmE_F9SsTpFxjGw"

CHANAKYA_URL = "http://0.0.0.0:8000/v1/retrieve"
CSV_FILE = "intel_feed.csv"

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Chanakya Defence Grid",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for the "War Room" look
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #00ff00; }
    div.stButton > button { background-color: #ff4b4b; color: white; border-radius: 5px; }
    h1 { color: #ff4b4b; text-align: center; font-family: 'Courier New'; }
    .report-box { border: 1px solid #333; padding: 10px; border-radius: 5px; margin-bottom: 10px; background-color: #1e1e1e; }
</style>
""", unsafe_allow_html=True)

# --- GEMINI SETUP (Auto-Discovery from Phase 2) ---
if "AIza" not in GEMINI_API_KEY:
    st.error("⚠️ API Key missing in app.py!")
    st.stop()

@st.cache_resource
def setup_gemini():
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        # Quick model scan
        models = list(client.models.list())
        for m in models:
            if "flash" in m.name and "vision" not in m.name:
                return client, m.name.replace("models/", "")
        return client, "gemini-1.5-flash" # Fallback
    except Exception as e:
        return None, str(e)

client, active_model = setup_gemini()

# --- BACKEND FUNCTIONS ---
def get_intel_from_chanakya(query):
    try:
        response = requests.post(CHANAKYA_URL, json={"query": query, "k": 3})
        data = response.json()
        if not data: return []
        return [item['text'] for item in data]
    except:
        return None

def ask_commander(query, context):
    system_prompt = f"""
    You are Major Chanakya. 
    LIVE INTEL: {context}
    USER QUERY: {query}
    MISSION: Answer as a Military Commander. Be brief. High threats = UPPERCASE.
    Start with "COMMANDER:"
    """
    try:
        res = client.models.generate_content(model=active_model, contents=system_prompt)
        return res.text
    except Exception as e:
        return f"Comms Failure: {e}"

# --- DASHBOARD LAYOUT ---

# HEADER
st.title("🛡️ CHANAKYA DEFENCE GRID")
st.caption(f"System Status: ONLINE | AI Model: {active_model} | RAG Engine: ACTIVE")

# SIDEBAR: LIVE FEED
with st.sidebar:
    st.header("📡 Live Intel Feed")
    if st.button("🔄 Refresh Data"):
        st.rerun()
    
    # Read CSV directly for the sidebar display
    try:
        df = pd.read_csv(CSV_FILE)
        # Show latest 5 entries
        for index, row in df.tail(5).iloc[::-1].iterrows():
            priority_color = "🔴" if row['priority'] == 'High' else "🟢"
            st.markdown(f"""
            <div class="report-box">
                <b>{priority_color} {row['timestamp']}</b><br>
                <small>{row['sector']} Sector</small><br>
                {row['report']}
            </div>
            """, unsafe_allow_html=True)
    except:
        st.warning("Waiting for data stream...")

# MAIN AREA: MAP & CHAT
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📍 Tactical Map (Northern Sector)")
    # Fake map data for visuals (Centered on Kashmir region coordinates)
    map_data = pd.DataFrame({
        'lat': [34.0837, 34.1, 33.9, 34.2],
        'lon': [74.7973, 74.8, 74.6, 74.9],
        'type': ['base', 'threat', 'patrol', 'threat']
    })
    st.map(map_data, zoom=8, color="#ff0000")

with col2:
    st.subheader("💬 Command Link")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Enter command..."):
        # User message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI Response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing Intel..."):
                # 1. Get RAG Context
                context_list = get_intel_from_chanakya(prompt)
                
                if context_list is None:
                    response = "⚠️ Connection to Chanakya Server Lost. Check backend."
                elif not context_list:
                    response = "COMMANDER: No intelligence found on this topic."
                else:
                    context_str = "\n".join(context_list)
                    # 2. Get AI Voice
                    response = ask_commander(prompt, context_str)
            
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})