import os
import streamlit as st
from groq import Groq
import pypdf

# 1. Page Configuration
st.set_page_config(
    page_title="OmniMind Assistant",
    page_icon="🧠",
    layout="centered"
)

# 2. Custom Light & Readable Theme Styling
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #f0f7f7;
        color: #0f2537;
    }
    
    /* Header & Titles */
    h1, h2, h3, p {
        color: #0f2537 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* User Chat Bubble */
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #dbeafe;
        border-radius: 12px;
        padding: 10px;
        color: #0f2537;
    }

    /* AI Chat Bubble */
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 10px;
        color: #0f2537;
    }
</style>
""", unsafe_allow_html=True)

# 3. Retrieve API Key securely from Secrets
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("API Key missing! Please set GROQ_API_KEY in your Streamlit secrets.")
    st.stop()

client = Groq(api_key=api_key)

# 4. Initialize Chat Session State
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am OmniMind Assistant. Upload a document or ask me anything!"}
    ]

if "file_context" not in st.session_state:
    st.session_state.file_context = ""

# 5. Sidebar for File Upload & Controls
with st.sidebar:
    st.title("📎 Attachments")
    uploaded_file = st.file_uploader("Upload a document (.pdf or .txt)", type=["pdf", "txt"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".pdf"):
                pdf_reader = pypdf.PdfReader(uploaded_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() or ""
                st.session_state.file_context = text
            elif uploaded_file.name.endswith(".txt"):
                st.session_state.file_context = uploaded_file.read().decode("utf-8")
                
            st.success(f"Loaded: {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    if st.button("Clear Chat History"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Chat history cleared. How can I help you next?"}
        ]
        st.session_state.file_context = ""
        st.rerun()

# 6. UI Header
st.title("🧠 OmniMind Assistant")
st.caption("Powered by Groq & Llama 3.3")

# 7. Render Existing Chat Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 8. Handle New User Input
if prompt := st.chat_input("Ask anything or ask about your uploaded file..."):
    # Append & display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build conversation payload with file context if available
    api_messages = []
    
    if st.session_state.file_context:
        system_prompt = (
            "You have access to the following document content provided by the user. "
            "Use it to answer their questions when relevant:\n\n"
            f"--- DOCUMENT START ---\n{st.session_state.file_context[:8000]}\n--- DOCUMENT END ---"
        )
        api_messages.append({"role": "system", "content": system_prompt})
        
    for m in st.session_state.messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    # Generate AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=api_messages,
                temperature=0.7,
                stream=True
            )
            
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # Save assistant response to session state
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error communicating with AI: {e}")