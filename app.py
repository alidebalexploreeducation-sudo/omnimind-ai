import os
import uuid
import urllib.parse
import datetime
import requests
import streamlit as st
import pypdf
import docx
import pandas as pd
from groq import Groq

# ---------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="OmniMind Assistant",
    page_icon="🧠",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stHeader"] {display: none !important;}

    /* User Chat Bubble */
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

    /* Assistant Chat Bubble */
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
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Session State Setup
# ---------------------------------------------------------
if "user_chats" not in st.session_state:
    initial_id = str(uuid.uuid4())
    st.session_state.user_chats = {
        initial_id: {
            "title": "New Chat",
            "messages": [
                {"role": "assistant", "content": "Hello! I am OmniMind Assistant, created by Ali Debal. Ask me anything, generate images, attach files, or enable Guided Learning!"}
            ]
        }
    }
    st.session_state.current_chat_id = initial_id

if "file_context" not in st.session_state:
    st.session_state.file_context = ""

if "active_mode" not in st.session_state:
    st.session_state.active_mode = "Standard"

# ---------------------------------------------------------
# 3. API & Utility Functions
# ---------------------------------------------------------
groq_api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")

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
# 4. Sidebar Navigation
# ---------------------------------------------------------
with st.sidebar:
    st.title("🧠 OmniMind")
    st.caption(f"⚡ Live Sync | {datetime.datetime.now().strftime('%H:%M:%S')}")

    if st.button("➕ New chat", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        st.session_state.user_chats[new_id] = {
            "title": "New Chat",
            "messages": [
                {"role": "assistant", "content": "Hello! I am OmniMind Assistant, created by Ali Debal. Ask me anything!"}
            ]
        }
        st.session_state.current_chat_id = new_id
        st.session_state.file_context = ""
        st.session_state.active_mode = "Standard"
        st.rerun()

    st.divider()
    st.markdown("### 📚 Chat Library")

    user_chats = st.session_state.user_chats
    for cid in reversed(list(user_chats.keys())):
        chat_title = user_chats[cid].get("title", "New Chat")
        display_title = (chat_title[:18] + "...") if len(chat_title) > 18 else chat_title
        is_active = (cid == st.session_state.current_chat_id)
        btn_label = f"👈 {display_title}" if is_active else f"💬 {display_title}"
        
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
# 5. Main Content Area
# ---------------------------------------------------------
current_chat = st.session_state.user_chats[st.session_state.current_chat_id]
messages = current_chat["messages"]

st.title(current_chat.get("title", "OmniMind Assistant"))
st.caption("Powered by Auto-Failover AI | Built by Ali Debal")

# Render History Messages
for msg in messages:
    with st.chat_message(msg["role"]):
        if msg.get("image_url"):
            st.image(msg["image_url"], caption="Generated Image")
        if msg.get("content"):
            st.markdown(msg["content"])

# ---------------------------------------------------------
# 6. Quick Actions Bar
# ---------------------------------------------------------
st.markdown("### ➕ Quick Actions Bar")

c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("🎨 Create Image Mode", use_container_width=True):
        st.session_state.active_mode = "Image"
        st.toast("Image Generation Mode Active!")
with c2:
    if st.button("📑 Canvas Mode", use_container_width=True):
        st.session_state.active_mode = "Canvas"
        st.toast("Canvas Mode Active!")
with c3:
    if st.button("🎓 Guided Learning", use_container_width=True):
        st.session_state.active_mode = "Guided"
        st.toast("Guided Learning Active!")
with c4:
    if st.button("🔄 Standard Mode", use_container_width=True):
        st.session_state.active_mode = "Standard"
        st.toast("Standard Mode Active!")

st.caption(f"Current Active Mode: **{st.session_state.active_mode} Mode**")

# File Uploader Optional Accordion
with st.expander("📎 Attach Document (PDF, DOCX, TXT, CSV, XLSX)"):
    up_file = st.file_uploader("Upload document context", type=["pdf", "docx", "txt", "csv", "xlsx"], label_visibility="collapsed")
    if up_file:
        st.session_state.file_context = extract_file_text(up_file)
        st.success(f"Attached: {up_file.name}")

# Standard Bottom Input Box
prompt = st.chat_input("Ask anything, attach files, or type image prompts...")

if prompt:
    if len(messages) <= 1 or current_chat.get("title") == "New Chat":
        current_chat["title"] = prompt[:25] + ("..." if len(prompt) > 25 else "")

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
            sys_prompt += " Act as a helpful tutor guiding the user step-by-step."
        elif st.session_state.active_mode == "Canvas":
            sys_prompt += " Structure responses with clear headings, lists, and summary blocks."

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
                    messages.append({"role": "assistant", "content": full_text})
                    st.rerun()
                except Exception as e:
                    st.error(f"Error processing request: {e}")