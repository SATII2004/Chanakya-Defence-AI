🛡️ C.H.A.N.A.K.Y.A. Defence-AI
Command Hub for Advanced Network Analysis & Kinetic Yield Assessment
![Status](https://img.shields.io/badge/STATUS-OPERATIONAL-brightgreen?style=for-the-badge&logo=rss)
![Security](https://img.shields.io/badge/SECURITY-AES--256-blue?style=for-the-badge&logo=lock)
![AI](https://img.shields.io/badge/AI-PATHWAY%20RAG-orange?style=for-the-badge&logo=python)
![Voice](https://img.shields.io/badge/VOICE-NEURAL%20TTS-purple?style=for-the-badge&logo=waveform)
🧠 Overview

C.H.A.N.A.K.Y.A. is a next-generation Integrated Command & Control System (ICCS) designed for modern hybrid and information warfare.

It provides a centralized, real-time command dashboard connecting the Chief of Defence Staff (CDS) with Field Agents across Army, Navy, and Air Force units.

At its core, the system is powered by a Live Retrieval-Augmented Generation (RAG) engine built using Pathway, allowing the AI to reason over real-time battlefield intelligence streams rather than static training data.

🚀 Strategic Capabilities
🧠 1. Live Thinking Engine (Pathway RAG)

Real-Time Context Awareness
Unlike conventional LLMs, Chanakya continuously ingests live intel feeds.

Instant Vector Updates
New reports are immediately embedded and indexed.

True Live Intelligence
Queries like “What is the latest threat?” are answered using data from seconds ago, not historical knowledge.

Hybrid AI Stack

SentenceTransformers → Local, unlimited embeddings

Google Gemini 1.5 / 2.5 Flash → Strategic reasoning

🗺️ 2. 3D Kinetic Battlespace

Live Asset Visualization
Displays all 17 Indian Command HQs (Army, Navy, Air Force).

3D Tactical Map
Built using PyDeck with terrain-aware rendering.

Threat Plotting
High-priority hostile intel appears as pulsating red skulls on the map.

🗣️ 3. “Jarvis” Neural Command Voice

Military-Grade Voice Output

Powered by Microsoft Edge TTS

Voice: en-IN-PrabhatNeural

Deep Command Tone

Pitch shifted by -15Hz

Designed for realistic War Room feedback

👁️ 4. Trinetra – Satellite Recon Module

Vision Intelligence

Analyzes drone & satellite imagery

Target Identification

Detects terrain risks, enemy assets, and concealment

Model

Gemini 2.5 Flash (Vision)

🌐 5. OSINT Radar

Live OSINT Stream

Simulated global news & intercept feeds

AI Truth Verification

Cross-checks rumors against live RAG knowledge base

Confidence Scoring

Assigns credibility levels to field reports

🛠️ Technology Stack
Layer	Technology
Core RAG Engine	Pathway (Real-Time Data Processing)
LLM Orchestration	LiteLLM + Google Gemini 2.5 Flash
Vector Indexing	SentenceTransformers (Local Embeddings)
Frontend	Streamlit (Glassmorphism UI)
Voice Engine	Edge TTS + AsyncIO
Visualization	PyDeck (3D Maps), Plotly (Radar)
⚡ Installation & Setup
1️⃣ Clone the Repository
git clone https://github.com/SATII2004/Chanakya-Defence-AI.git
cd Chanakya-Defence-AI

2️⃣ Install Dependencies
pip install -r requirements.txt


Required packages include:

pathway

litellm

sentence-transformers

streamlit

newsapi-python

3️⃣ Configure Credentials

Create a .env file in the root directory:

GEMINI_API_KEY=your_actual_google_api_key_here

4️⃣ Initialize Assets
mkdir assets live_data

🛰️ Launch Mission
(Three-Terminal Execution Sequence)

To demonstrate Live RAG capabilities, all components must run simultaneously.

🧠 Terminal 1 – The Brain (Pathway Backend)

Starts the vector store and REST API.

python backend.py


Expected log:

🚀 Pathway Engine Starting on 0.0.0.0:8000...

👁️ Terminal 2 – The Eyes (Intel Streamer)

Simulates real-time intel ingestion.

python news_streamer.py

🛡️ Terminal 3 – The Command Center (UI)

Launches the dashboard.

streamlit run app.py

📸 System Modules
Module	Function
💬 COMMS	Strategic queries to Pathway Live RAG
⚔️ ORDERS	Issue directives to military units
📡 RADAR	Aerial threat visualization
📂 VEDA	PDF intelligence document analysis
👁️ TRINETRA	Satellite & drone image analysis
🌐 OSINT	Public sentiment & intel verification
📜 Philosophy

“Strategy without tactics is the slowest route to victory.
Tactics without strategy is the noise before defeat.”
— Sun Tzu

© 2026 Defence Research & Development (Concept Project)