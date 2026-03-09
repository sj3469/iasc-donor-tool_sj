import os
import sys
from pathlib import Path
import streamlit as st

# --- THE PATH BRIDGE ---
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# --- PROJECT IMPORTS ---
import config
from llm import get_response
from token_tracker import SessionTracker

APP_TITLE = getattr(config, "APP_TITLE", "IASC Donor Analytics")
APP_SUBTITLE = getattr(config, "APP_SUBTITLE", "AI-powered donor intelligence")
AVAILABLE_MODELS = getattr(config, "AVAILABLE_MODELS", {"gemini-2.0-flash": "Gemini 2.0 Flash"})
DEFAULT_MODEL = getattr(config, "DEFAULT_MODEL", list(AVAILABLE_MODELS.keys())[0])
DB_PATH = root_dir / "data" / "donors.db"

# --- PAGE CONFIG ---
st.set_page_config(page_title=APP_TITLE, page_icon="●", layout="wide", initial_sidebar_state="expanded")

# --- DATABASE AUTO-BUILDER ---
if not DB_PATH.exists():
    with st.spinner("Building the IASC donor database..."):
        try:
            script_path = root_dir / "data" / "generate_mock_data.py"
            if script_path.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("generate_mock", script_path)
                mock_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mock_module)
                mock_module.main()
        except Exception as e:
            st.error(f"Failed to generate database: {e}")

# --- CSS INJECTION ---
def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root { --bg: #0b1020; --panel: #12182b; --panel-2: #161d33; --border: #27314a; --text: #e8ecf7; --muted: #9aa4bf; }
        .stApp { background: var(--bg); color: var(--text); }
        [data-testid="stSidebar"] { background: #0f1527; border-right: 1px solid var(--border); }
        [data-testid="stSidebar"] * { color: var(--text); }
        h1, h2, h3, h4, p, span, label, div { color: var(--text); }
        div[data-testid="stTextInput"] input, textarea, input, div[data-baseweb="select"] {
            background-color: var(--panel); color: var(--text); border: 1px solid var(--border);
        }
        .app-subtitle { color: var(--muted); margin-top: -0.25rem; margin-bottom: 1rem; font-size: 0.98rem; }
        
        /* Custom FAQ Button Styling */
        div[data-testid="stButton"] button {
            background-color: var(--panel-2);
            border: 1px solid var(--border);
            color: var(--text);
            width: 100%;
            text-align: left;
        }
        div[data-testid="stButton"] button:hover {
            border-color: #7c8cff;
            color: #7c8cff;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
inject_css()

# --- INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tracker" not in st.session_state:
    st.session_state.tracker = SessionTracker()
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Settings")
    selected_model = st.selectbox("Model", list(AVAILABLE_MODELS.keys()), index=0)
    st.divider()
    st.markdown("### 🔍 Quick Filters")
    donor_status = st.selectbox("Donor Status", ["All", "Active", "Lapsed", "Prospect"])
    state_filter = st.selectbox("State", ["All", "VA", "NY", "CA", "TX"])
    st.divider()
    
    # 🌟 CRITICAL FIX: The live-updating placeholder for token usage
    tracker_placeholder = st.empty()
    try:
        tracker_placeholder.markdown(st.session_state.tracker.format_sidebar())
    except Exception:
        pass 
        
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# --- MAIN UI ---
st.title(APP_TITLE)
st.markdown(f'<p class="app-subtitle">{APP_SUBTITLE}</p>', unsafe_allow_html=True)

# 🌟 NEW UX: FAQ Starter Prompts (Appear only when chat is empty)
if not st.session_state.messages:
    st.markdown("### 💡 Frequently Asked Questions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏆 Who are the top 10 donors by lifetime giving?"):
            st.session_state.pending_prompt = "Who are the top 10 donors by lifetime giving?"
            st.rerun()
        if st.button("📊 Can you provide a summary of giving statistics?"):
            st.session_state.pending_prompt = "Can you provide a summary of our giving statistics?"
            st.rerun()
    with col2:
        if st.button("⚠️ Show me lapsed donors who haven't given since 2023"):
            st.session_state.pending_prompt = "Show me lapsed donors who haven't given since 2023."
            st.rerun()
        if st.button("🗺️ Show me the geographic distribution of our donors"):
            st.session_state.pending_prompt = "Show me the geographic distribution of our donors."
            st.rerun()

# Render existing messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- CHAT INPUT & FILE UPLOADER ---
# 🌟 NEW UX: accept_file=True puts the '+' icon directly inside the chat bar
try:
    prompt_input = st.chat_input("Ask about your donor community...", accept_file=True)
except TypeError:
    prompt_input = st.chat_input("Ask about your donor community...")
    st.info("💡 Tip: To get the '+' file upload icon inside this chat bar, run `pip install --upgrade streamlit`.")

active_prompt = None
uploaded_file = None

if prompt_input:
    # Streamlit 1.43+ returns a dict-like object. Older versions return a plain string.
    if isinstance(prompt_input, str):
        active_prompt = prompt_input
    else:
        active_prompt = prompt_input.text
        uploaded_file = prompt_input.files[0] if prompt_input.files else None
        if not active_prompt and uploaded_file:
            active_prompt = f"Please analyze this attached file: {uploaded_file.name}"
elif st.session_state.pending_prompt:
    active_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if active_prompt:
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    with st.chat_message("user"):
        st.markdown(active_prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        with st.status("Consulting IASC records...", expanded=True) as status:
            response, usage = get_response(
                user_message=active_prompt,
                conversation_history=st.session_state.messages[:-1],
                model=selected_model,
                session_tracker=st.session_state.tracker,
                attachment=uploaded_file
            )
            status.update(label="Complete!", state="complete", expanded=False)
        
        response_placeholder.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # 🌟 CRITICAL FIX: Live-update the sidebar tracker immediately
        tracker_placeholder.markdown(st.session_state.tracker.format_sidebar())
