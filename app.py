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
# 2. Custom Styling & Dark Mode Rules
# ---------------------------------------------------------
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stHeader"] {display: none !important;}

    /* User Message Alignment (Right) */
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

    /* Assistant Message Alignment (Left) */
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
# 3. Private Session State Management
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

if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False

# ---------------------------------------------------------
# 4. API & Speech Setup
# ---------------------------------------------------------
groq_api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
elevenlabs_key = st.secrets.get("ELEVENLABS_API_KEY") or os.getenv("ELEVENLABS_API_KEY")

if not groq_api_key:
    st.error("GROQ_API_KEY missing! Please configure it in Streamlit Secrets.")
    st.stop()

client = Groq(api_key=groq_api_key)
MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]

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

def generate_natural_voice(text):
    """Converts text to human-like voice using ElevenLabs API."""
    if not elevenlabs_key:
        return None
    
    # Default voice ID: "21m00Tcm4TlvDq8ikWAM" (Rachel)
    voice_id = "21m00Tcm4TlvDq8ikWAM"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": elevenlabs_key
    }
    data = {
        "text": text[:1000],  # Limit length for performance
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_status == 200:
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
# 5. Sidebar Navigation
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

    st.markdown("### 🎙️ Audio Settings")
    st.session_state.voice_enabled = st.toggle("Enable Voice Call Mode (Read Responses Aloud)", value=st.session_state.voice_enabled)

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
# 6. Main Chat Area
# ---------------------------------------------------------
current_chat = st.session_state.user_chats[st.session_state.current_chat_id]
messages = current_chat["messages"]

st.title(current_chat.get("title", "OmniMind Assistant"))
st.caption("Created & Powered by Ali Debal")

# Render Messages
for msg in messages:
    with st.chat_message(msg["role"]):
        if msg.get("image_url"):
            st.image(msg["image_url"], caption="Generated Image")
        if msg.get("content"):
            st.markdown(msg["content"])
        if msg.get("audio"):
            st.audio(msg["audio"], format="audio/mp3")

# Web Speech Dictation Tool
speech_dictation_html = """
<div style="font-family: sans-serif; margin-top: 15px; margin-bottom: 5px;">
    <button onclick="startDictation()" style="padding: 8px 14px; border-radius: 8px; border: none; background: #3b82f6; color: white; font-weight: bold; cursor: pointer;">
        🎤 Click to Speak (Voice Input)
    </button>
    <span id="speech-status" style="font-size: 13px; color: #64748b; margin-left: 10px;"></span>
</div>

<script>
    function startDictation() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            var recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            document.getElementById('speech-status').innerText = 'Listening... Speak now.';
            recognition.start();

            recognition.onresult = function(e) {
                var transcript = e.results[0][0].transcript;
                document.getElementById('speech-status').innerText = 'Copied to clipboard!';
                navigator.clipboard.writeText(transcript);
                alert('Spoken prompt copied to clipboard: "' + transcript + '". Paste it into the input box below!');
            };

            recognition.onerror = function(e) {
                document.getElementById('speech-status').innerText = 'Error: ' + e.error;
            };
        } else {
            alert('Web Speech API is not supported in this browser. Use Chrome or Edge.');
        }
    }
</script>
"""
components.html(speech_dictation_html, height=60)

# Input Controls
action_col, input_col = st.columns([0.15, 0.85])

with action_col:
    with st.popover("➕ Options", use_container_width=True):
        st.markdown("### Quick Actions")
        up_file = st.file_uploader("Upload File", type=["pdf", "docx", "txt", "csv", "xlsx"])
        if up_file:
            st.session_state.file_context = extract_file_text(up_file)
            st.success(f"Attached: {up_file.name}")

        st.divider()
        if st.button("🎨 Create Image Mode", use_container_width=True):
            st.session_state.active_mode = "Image"
            st.toast("Image Generation Mode Active!")

        if st.button("📝 Canvas Mode", use_container_width=True):
            st.session_state.active_mode = "Canvas"
            st.toast("Canvas Mode Active!")

        if st.button("🎓 Guided Learning Mode", use_container_width=True):
            st.session_state.active_mode = "Guided"
            st.toast("Guided Learning Active!")

        if st.button("🔄 Reset Mode", use_container_width=True):
            st.session_state.active_mode = "Standard"
            st.toast("Standard Mode Active!")

with input_col:
    prompt = st.chat_input("Ask anything, attach files, or type image prompts...")

# Single-execution Prompt Handler
if prompt:
    if len(messages) <= 1 or current_chat.get("title") == "New Chat":
        current_chat["title"] = prompt[:30] + ("..." if len(prompt) > 30 else "")

    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if st.session_state.active_mode == "Image" or is_image_request(prompt):
        with st.chat_message("assistant"):
            with st.spinner("🎨 Generating image..."):
                encoded_prompt = urllib.parse.quote(prompt)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
                response_text = f"Here is your generated image for: *\"{prompt}\"*"
                st.markdown(response_text)
                st.image(image_url, caption=prompt)
                messages.append({"role": "assistant", "content": response_text, "image_url": image_url})
    else:
        sys_prompt = "You are OmniMind Assistant, created by Ali Debal. Never claim to be made by OpenAI, Meta, or Google."
        if st.session_state.active_mode == "Guided":
            sys_prompt += " Act as a tutor step-by-step."
        elif st.session_state.active_mode == "Canvas":
            sys_prompt += " Format responses in structured layout blocks."

        api_messages = [{"role": "system", "content": sys_prompt}]
        if st.session_state.file_context:
            api_messages.append({"role": "system", "content": f"Document Context:\n{st.session_state.file_context[:10000]}"})
        
        for m in messages:
            if m.get("content"):
                api_messages.append({"role": m["role"], "content": m["content"]})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    completion = query_ai_with_fallback(api_messages)
                    full_text = completion.choices[0].message.content
                    st.markdown(full_text)
                    
                    msg_data = {"role": "assistant", "content": full_text}
                    
                    if st.session_state.voice_enabled:
                        audio_bytes = generate_natural_voice(full_text)
                        if audio_bytes:
                            st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                            msg_data["audio"] = audio_bytes
                    
                    messages.append(msg_data)
                except Exception as e:
                    st.error(f"Error processing request: {e}")