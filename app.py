import os
import streamlit as st
from groq import Groq
import pypdf
import docx
import pandas as pd

# 1. Page Configuration
st.set_page_config(
    page_title="OmniMind Assistant",
    page_icon="🧠",
    layout="centered"
)

# 2. Custom Styling
st.markdown("""
<style>
    .stApp {
        background-color: #f0f7f7;
        color: #0f2537;
    }
    h1, h2, h3, p {
        color: #0f2537 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #dbeafe;
        border-radius: 12px;
        padding: 10px;
        color: #0f2537;
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 10px;
        color: #0f2537;
    }
</style>
""", unsafe_allow_html=True)

# 3. Retrieve API Key
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("API Key missing! Please set GROQ_API_KEY in your Streamlit secrets.")
    st.stop()

client = Groq(api_key=api_key)

# 4. Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am OmniMind Assistant. Upload any file (PDF, Word, TXT, CSV, Excel) or ask me anything!"}
    ]

if "file_context" not in st.session_state:
    st.session_state.file_context = ""

# Helper function to extract text from files
def extract_file_text(uploaded_file):
    fname = uploaded_file.name.lower()
    
    # PDF
    if fname.endswith(".pdf"):
        pdf_reader = pypdf.PdfReader(uploaded_file)
        return "".join([page.extract_text() or "" for page in pdf_reader.pages])
    
    # Word Document
    elif fname.endswith(".docx") or fname.endswith(".doc"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    
    # Plain Text
    elif fname.endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    
    # CSV Data
    elif fname.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        return f"CSV Data Summary:\n{df.to_string(index=False)}"
    
    # Excel Spreadsheet
    elif fname.endswith(".xlsx") or fname.endswith(".xls"):
        df = pd.read_excel(uploaded_file)
        return f"Excel Data Summary:\n{df.to_string(index=False)}"
    
    else:
        return "Unsupported file type."

# 5. Sidebar Options
with st.sidebar:
    st.title("📎 Attachments")
    uploaded_file = st.file_uploader(
        "Upload a document", 
        type=["pdf", "docx", "doc", "txt", "csv", "xlsx"]
    )
    
    if uploaded_file is not None:
        try:
            text = extract_file_text(uploaded_file)
            st.session_state.file_context = text
            st.success(f"Successfully loaded: {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    if st.button("Clear Chat History"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Chat history cleared. How can I help you next?"}
        ]
        st.session_state.file_context = ""
        st.rerun()

# 6. Title Header
st.title("🧠 OmniMind Assistant")
st.caption("Powered by Groq & Llama 3.3")

# 7. Render Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 8. User Interaction
if prompt := st.chat_input("Ask anything or ask about your uploaded file..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    api_messages = []
    
    # Include uploaded document context
    if st.session_state.file_context:
        system_prompt = (
            "You are OmniMind Assistant. You have access to the document provided below. "
            "Use its context when helpful to answer questions:\n\n"
            f"--- DOCUMENT START ---\n{st.session_state.file_context[:10000]}\n--- DOCUMENT END ---"
        )
        api_messages.append({"role": "system", "content": system_prompt})
    
    for m in st.session_state.messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

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
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error communicating with AI: {e}")