import os
import uuid
import urllib.parse
import datetime
import requests
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
import pypdf
import docx
import pandas as pd

# ---------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="OmniMind Assistant",
    page_icon="🧠",
    layout="wide"
)

# ---------------------------------------------------------
# 2. Custom Styling & Fixed Layout
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Hide top Streamlit UI elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stHeader"] {display: none !important;}

    /* Chat bubble user - RIGHT */
    div[data-testid="stChatMessage"]:has(div[aria-label="Chat message opacity user"]) {
        flex-direction: row-reverse !important;
        text-align: right !important;
        background-color: #dbeafe !important;
        border-radius: 18px 18px 2px 18px !important;
        margin-left: auto !important;
        margin-right: 0 !important;
        max-width: 80% !important;
        padding: 12px 16px !important;
        color: #0f172a !important;
    }

    /* Chat bubble assistant - LEFT */
    div[data-testid="stChatMessage"]:has(div[aria-label="Chat message opacity assistant"]) {
        flex-direction: row !important;
        text-align: left !important;
        background-color: #f1f5f9 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 18px 18px 18px 2px !important;
        margin-right: auto !important;
        margin-left: 0 !important;
        max-width: 80% !important;
        padding: 12px 16px !important;
        color: #0f172a !important;
    }

    @media (prefers-color-scheme: dark) {
        .stApp {
            background-color: #0f172a !important;
            color: #f8fafc !important;
        }
        div[data-testid="stChatMessage"]:has(div[aria-label="Chat message opacity user"]) {
            background-color: #1e3a8a !important;
            color: #ffffff !important;
        }
        div[data-testid="stChatMessage"]:has(div[aria-label="Chat message opacity assistant"]) {
            background-color: #1e293b !important;
            border-color: #334155 !important;
            color: #f8fafc !important;
        }
        p, span, h1, h2, h3, h4, h5, h6, label {
            color: #f8fafc !important;
        }
    }

    .stButton > button {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. Session State Init
# ---------------------------------------------------------
if "user_chats" not in st.session_state:
    initial_id = str(uuid.uuid4())
    st.session_state.user_chats = {
        initial_id: {
            "title": "New Chat",
            "messages": [
                {"role": "assistant", "content": "Hello! I am OmniMind Assistant, created by Ali Debal. How can I assist you today?"}
            ]
        }
    }
    st.session_state.current_chat_id = initial_id

if "file_context" not in st.session_state:
    st.session_state.file_context = ""

if "active_mode" not in st.session_state:
    st.session_state.active_mode = "Standard"

if "selected_voice_id" not in st.session_state:
    st.session_state.selected_voice_id = "21m00Tcm4TlvDq8ikWAM" # Rachel

if "auto_speak" not in st.session_state:
    st.session_state.auto_speak = False

# ---------------------------------------------------------
# 4. API Configurations
# ---------------------------------------------------------
groq_api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
elevenlabs_key = st.secrets.get("ELEVENLABS_API_KEY") or os.getenv("ELEVENLABS_API_KEY")

if not groq_api_key:
    st.error("GROQ_API_KEY missing! Please configure it in Streamlit Secrets.")
    st.stop()

client = Groq(api_key=groq_api_key)
MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]

VOICE_OPTIONS = {
    "Rachel (Calm & Natural Female)": "21m00Tcm4TlvDq8ikWAM",
    "Adam (Deep & Professional Male)": "pNInz6obpgDQGcFmaJgB",
    "Antoni (Friendly Male)": "ErXwobaYiN019PkySvjV",
    "Bella (Expressive Female)": "EXAVITQu4vr4xnSDxMaL"
}

def query_ai_with_fallback(api_messages):
    for model_id in MODELS:
        try:
            return client.chat.completions.create(
                model=model_id,
                messages=api_messages,
                temperature=0.7,
                stream=False
            )
        except Exception:
            continue
    raise Exception("All AI backends are currently unreachable.")

def generate_natural_voice(text, voice_id):
    if not elevenlabs_key:
        return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": elevenlabs_key
    }
    data = {
        "text": text[:800],
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.content
    except Exception:
        pass
    return None

def extract_file_text(uploaded_file):
    fname = uploaded_file.name.lower()
    if fname.endswith(".pdf"):
        reader = pypdf.PdfReader(uploaded_file)
        return "".join([page.extract_text() or "" for page in reader.pages])
    elif fname.endswith(".docx") or fname.endswith(".doc"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif fname.endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    elif fname.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        return f"CSV Data:\n{df.to_string(index=False)}"
    elif fname.endswith(".xlsx") or fname.endswith(".xls"):
        df = pd.read_excel(uploaded_file)
        return f"Excel Data:\n{df.to_string(index=False)}"
    return ""

def is_image_request(prompt):
    triggers = ["image", "picture", "photo", "draw", "generate image", "create an image"]
    return any(t in prompt.lower() for t in triggers)

# ---------------------------------------------------------
# 5. Sidebar Controls & Voice Settings
# ---------------------------------------------------------
with st.sidebar:
    st.title("🧠 OmniMind")
    st.caption(f"⚡ Session Active | {datetime.datetime.now().strftime('%H:%M:%S')}")

    if st.button("➕ New chat", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        st.session_state.user_chats[new_id] = {
            "title": "New Chat",
            "messages": [
                {"role": "assistant", "content": "Hello! I am OmniMind Assistant, created by Ali Debal. How can I assist you?"}
            ]
        }
        st.session_state.current_chat_id = new_id
        st.session_state.file_context = ""
        st.session_state.active_mode = "Standard"
        st.rerun()

    st.divider()

    st.markdown("### 🎙️ Voice & Call Settings")
    selected_voice_label = st.selectbox("AI Voice Persona", list(VOICE_OPTIONS.keys()))
    st.session_state.selected_voice_id = VOICE_OPTIONS[selected_voice_label]

    st.session_state.auto_speak = st.toggle("📞 Live Call Mode (Auto Read Answers)", value=st.session_state.auto_speak)

    st.divider()

    st.markdown("### 📚 Your Chats")
    user_chats = st.session_state.user_chats
    for cid in reversed(list(user_chats.keys())):
        chat_title = user_chats[cid].get("title", "New Chat")
        display_title = (chat_title[:20] + "...") if len(chat_title) > 20 else chat_title
        is_active = (cid == st.session_state.current_chat_id)
        btn_label = f"💬 {display_title}" if not is_active else f"👉 {display_title}"
        
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(btn_label, key=f"sel_{cid}", use_container_width=True):
                st.session_state.current_chat_id = cid
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{cid}"):
                del st.session_state.user_chats[cid]
                remaining = list(st.session_state.user_chats.keys())
                if remaining:
                    st.session_state.current_chat_id = remaining[-1]
                else:
                    nid = str(uuid.uuid4())
                    st.session_state.user_chats[nid] = {
                        "title": "New Chat",
                        "messages": [{"role": "assistant", "content": "How can I help you?"}]
                    }
                    st.session_state.current_chat_id = nid
                st.rerun()

# ---------------------------------------------------------
# 6. Main Chat Interface
# ---------------------------------------------------------
current_chat = st.session_state.user_chats[st.session_state.current_chat_id]
messages = current_chat["messages"]

st.title(current_chat.get("title", "OmniMind Assistant"))
st.caption("Created & Powered by Ali Debal")

# Display Messages with Individual Speaker Icon
for idx, msg in enumerate(messages):
    with st.chat_message(msg["role"]):
        if msg.get("image_url"):
            st.image(msg["image_url"], caption="Generated Image")
        if msg.get("content"):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                col_sp, _ = st.columns([0.1, 0.9])
                with col_sp:
                    if st.button("🔊 Listen", key=f"speak