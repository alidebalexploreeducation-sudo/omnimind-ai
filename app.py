import os
import json
import uuid
import urllib.parse
import datetime
import streamlit as st
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
# 2. Custom CSS (User Messages Right, Assistant Left)
# ---------------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }

    /* User Message Container - RIGHT */
    div[data-testid="stChatMessage"]:has(div[aria-label="Chat message opacity user"]) {
        flex-direction: row-reverse !important;
        text-align: right !important;
        background-color: #dbeafe !important;
        border-radius: 18px 18px 2px 18px !important;
        margin-left: auto !important;
        margin-right: 0 !important;
        max-width: 80% !important;
        padding: 12px 16px !important;
        color: #1e3a8a !important;
    }

    /* Assistant Message Container - LEFT */
    div[data-testid="stChatMessage"]:has(div[aria-label="Chat message opacity assistant"]) {
        flex-direction: row !important;
        text-align: left !important;
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 18px 18px 18px 2px !important;
        margin-right: auto !important;
        margin-left: 0 !important;
        max-width: 80% !important;
        padding: 12px 16px !important;
        color: #0f172a !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .stButton > button {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. Persistent Storage
# ---------------------------------------------------------
CHAT_FILE = "chats.json"

def load_all_chats():
    if os.path.exists(CHAT_FILE):
        try:
            with open(CHAT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_all_chats(chats):
    with open(CHAT_FILE, "w") as f:
        json.dump(chats, f, indent=2)

if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_all_chats()

if "current_chat_id" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.all_chats[new_id] = {
        "title": "New Chat",
        "messages": [
            {"role": "assistant", "content": "Hello! I am OmniMind Assistant, created by Ali Debal. Ask me anything, generate images, attach files, or enable Guided Learning!"}
        ]
    }
    st.session_state.current_chat_id = new_id
    save_all_chats(st.session_state.all_chats)

if "file_context" not in st.session_state:
    st.session_state.file_context = ""

if "active_mode" not in st.session_state:
    st.session_state.active_mode = "Standard"

# ---------------------------------------------------------
# 4. API & Auto-Failover System
# ---------------------------------------------------------
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("GROQ_API_KEY missing! Please add it in your Streamlit secrets.")
    st.stop()

client = Groq(api_key=api_key)

MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]

def query_ai_with_fallback(api_messages):
    for model_id in MODELS:
        try:
            return client.chat.completions.create(
                model=model_id,
                messages=api_messages,
                temperature=0.7,
                stream=True
            )
        except Exception:
            continue
    raise Exception("All model backends are currently unreachable.")

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
    p = prompt.lower()
    triggers = ["image", "picture", "photo", "draw", "generate", "create an image"]
    return any(t in p for t in triggers)

# ---------------------------------------------------------
# 5. Sidebar (Gemini Style)
# ---------------------------------------------------------
with st.sidebar:
    st.title("🧠 OmniMind")
    st.caption(f"⚡ Live Sync | {datetime.datetime.now().strftime('%H:%M:%S')}")

    if st.button("➕ New chat", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {
            "title": "New Chat",
            "messages": [
                {"role": "assistant", "content": "Hello! I am OmniMind Assistant, created by Ali Debal. How can I help you today?"}
            ]
        }
        st.session_state.current_chat_id = new_id
        st.session_state.file_context = ""
        st.session_state.active_mode = "Standard"
        save_all_chats(st.session_state.all_chats)
        st.rerun()

    st.divider()

    search_query = st.text_input("🔍 Search chats", placeholder="Filter history...").strip().lower()

    st.markdown("### 📚 Chat Library")
    
    chats = st.session_state.all_chats
    matching_ids = []
    
    for cid, cdata in chats.items():
        title = cdata.get("title", "New Chat")
        if search_query:
            m_text = " ".join([m["content"] for m in cdata.get("messages", [])]).lower()
            if search_query in title.lower() or search_query in m_text:
                matching_ids.append(cid)
        else:
            matching_ids.append(cid)

    if not matching_ids:
        st.caption("No chats found.")
    else:
        for cid in reversed(matching_ids):
            chat_title = chats[cid].get("title", "New Chat")
            display_title = (chat_title[:20] + "...") if len(chat_title) > 20 else chat_title
            
            is_active = (cid == st.session_state.current_chat_id)
            btn_label = f"💬 {display_title}" if not is_active else f"👉 {display_title}"
            
            col1, col2 = st.columns([0.82, 0.18])
            with col1:
                if st.button(btn_label, key=f"select_{cid}", use_container_width=True):
                    st.session_state.current_chat_id = cid
                    st.session_state.file_context = ""
                    st.rerun()
            with col2:
                with st.popover("⋮"):
                    new_title = st.text_input("Rename chat", value=chat_title, key=f"rename_{cid}")
                    if st.button("Save Name", key=f"save_title_{cid}"):
                        chats[cid]["title"] = new_title
                        save_all_chats(chats)
                        st.rerun()
                    
                    st.divider()
                    if st.button("🗑️ Delete Chat", key=f"del_{cid}", type="primary"):
                        del st.session_state.all_chats[cid]
                        save_all_chats(st.session_state.all_chats)
                        remaining = list(st.session_state.all_chats.keys())
                        if remaining:
                            st.session_state.current_chat_id = remaining[-1]
                        else:
                            new_id = str(uuid.uuid4())
                            st.session_state.all_chats[new_id] = {
                                "title": "New Chat",
                                "messages": [{"role": "assistant", "content": "How can I help you?"}]
                            }
                            st.session_state.current_chat_id = new_id
                        st.rerun()

    st.divider()

    st.markdown("### 📎 File Attachments")
    uploaded_file = st.file_uploader("Upload document", type=["pdf", "docx", "doc", "txt", "csv", "xlsx"])
    if uploaded_file is not None:
        try:
            st.session_state.file_context = extract_file_text(uploaded_file)
            st.success(f"Attached: {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error reading file: {e}")

# ---------------------------------------------------------
# 6. Main Chat Area
# ---------------------------------------------------------
current_chat = st.session_state.all_chats[st.session_state.current_chat_id]
messages = current_chat["messages"]

st.title(current_chat.get("title", "OmniMind Assistant"))
st.caption("Powered by Auto-Failover AI | Built by Ali Debal")

for msg in messages:
    with st.chat_message(msg["role"]):
        if msg.get("image_url"):
            st.image(msg["image_url"], caption="Generated Image")
        if msg.get("content"):
            st.markdown(msg["content"])

st.markdown("#### ➕ Quick Actions Bar")
tool_col1, tool_col2, tool_col3, tool_col4 = st.columns(4)

with tool_col1:
    if st.button("🎨 Create Image Mode", use_container_width=True):
        st.session_state.active_mode = "Image"
        st.toast("Image Generation Mode Selected!")

with tool_col2:
    if st.button("🎨 Canvas Mode", use_container_width=True):
        st.session_state.active_mode = "Canvas"
        st.toast("Canvas Mode Enabled!")

with tool_col3:
    if st.button("🎓 Guided Learning", use_container_width=True):
        st.session_state.active_mode = "Guided"
        st.toast("Guided Learning Mode Activated!")

with tool_col4:
    if st.button("🔄 Standard Mode", use_container_width=True):
        st.session_state.active_mode = "Standard"
        st.toast("Standard Mode Selected!")

st.caption(f"Current Active Mode: **{st.session_state.active_mode} Mode**")

if prompt := st.chat_input("Ask anything, attach files, or type image prompts..."):
    if len(messages) <= 1 or current_chat.get("title") == "New Chat":
        auto_title = prompt[:30] + ("..." if len(prompt) > 30 else "")
        current_chat["title"] = auto_title

    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if st.session_state.active_mode == "Image" or is_image_request(prompt):
        with st.chat_message("assistant"):
            with st.spinner("🎨 Generating image..."):
                encoded_prompt = urllib.parse.quote(prompt)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
                
                response_text = f"Here is the image generated by OmniMind for: *\"{prompt}\"*"
                st.markdown(response_text)
                st.image(image_url, caption=prompt)
                
                messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "image_url": image_url
                })
                save_all_chats(st.session_state.all_chats)

    else:
        sys_prompt = "You are OmniMind Assistant, an advanced AI created and built by Ali Debal. Never claim to be made by Meta, OpenAI, or Google. You were created by Ali Debal."
        
        if st.session_state.active_mode == "Guided":
            sys_prompt += " Act as a patient tutor. Explain complex concepts step-by-step with clear examples and ask questions to make sure the user learns."
        elif st.session_state.active_mode == "Canvas":
            sys_prompt += " Format responses as clean, structured, modular blocks suitable for a digital canvas."

        api_messages = [{"role": "system", "content": sys_prompt}]
        
        if st.session_state.file_context:
            api_messages.append({
                "role": "system",
                "content": f"Use this attached document context if helpful:\n\n{st.session_state.file_context[:10000]}"
            })
        
        for m in messages:
            if m.get("content"):
                api_messages.append({"role": m["role"], "content": m["content"]})

        with st.chat_message("assistant"):
            placeholder = st.empty()
            try:
                response = query_ai_with_fallback(api_messages)
                full_text = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        full_text += chunk.choices[0].delta.content
                        placeholder.markdown(full_text + "▌")
                
                placeholder.markdown(full_text)
                messages.append({"role": "assistant", "content": full_text})
                save_all_chats(st.session_state.all_chats)
                
            except Exception as e:
                st.error(f"Error: {e}")