import streamlit as st
import os
from groq import Groq

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="OmniMind AI",
    page_icon="🧠",
    layout="wide"
)

# --- CLEAN & SOFT LIGHT THEME CSS ---
st.markdown("""
<style>
    /* Clean light background */
    .stApp {
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }
    
    /* Subtle Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f1f5f9 !important;
        border-right: 1px solid #e2e8f0;
    }

    /* Soft, readable input box */
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 12px !important;
        font-size: 16px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
    }

    /* Soft Blue Submit Button */
    .stButton > button {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        transition: background-color 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #1d4ed8 !important;
    }

    /* Clean Card for Responses */
    .answer-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #2563eb;
        border-radius: 8px;
        padding: 20px;
        margin-top: 15px;
        color: #1e293b;
        font-size: 16px;
        line-height: 1.6;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
</style>
""", unsafe_allow_html=True)

# Initialize Groq client safely
groq_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=groq_key) if groq_key else None

def get_web_context(query):
    """Safely fetch search context without throwing crashing errors on consecutive queries."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return "\n".join([f"- {r.get('title', '')}: {r.get('body', '')}" for r in results])
    except Exception:
        # Fallback gracefully if rate-limited or offline
        pass
    return "No search results available."

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ AI Controls")
    creativity = st.slider("Creativity Level", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
    st.markdown("---")
    st.caption("Powered by **Groq** & Meta **Llama 3.3**")

# --- MAIN CONTENT ---
st.title("🧠 OmniMind Assistant")
st.markdown("##### Ask any question across science, history, general knowledge, or world events.")

# Using session state to maintain clear consecutive inputs
with st.form("chat_form", clear_on_submit=False):
    user_input = st.text_input("Enter your question:", placeholder="e.g., How do airplanes stay in the air?")
    submitted = st.form_submit_button("Send ↵")

if submitted and user_input:
    if not client:
        st.error("API key not detected. Please run 'set GROQ_API_KEY=your_key' in your Command Prompt.")
    else:
        with st.spinner("Retrieving answer..."):
            try:
                web_context = get_web_context(user_input)
                prompt = f"Search Context:\n{web_context}\n\nUser Question:\n{user_input}"
                
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are OmniMind, a clear, accurate, and helpful knowledge assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=creativity
                )
                
                response_text = chat_completion.choices[0].message.content
                
                st.markdown(f"""
                <div class="answer-box">
                    <h4 style="color: #2563eb; margin-top: 0;">Answer</h4>
                    {response_text}
                </div>
                """, unsafe_allow_html=True)
                
                if web_context != "No search results available.":
                    st.write("")
                    with st.expander("🔍 View Web Context"):
                        st.text(web_context)

            except Exception as e:
                st.error(f"Error processing request: {str(e)}")