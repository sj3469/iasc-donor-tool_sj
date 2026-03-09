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
st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide", initial_sidebar_state="expanded")

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

# --- HELPER: CSV PARSER ---
def convert_to_csv(text):
    """Extracts markdown tables from the AI response and converts them to CSV."""
    lines = text.strip().split('\n')
    csv_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith('|') and line.endswith('|'):
            line = line[1:-1]
            if set(line.replace('|', '').replace('-', '').replace(' ', '')) == set():
                continue
            row = [col.strip().replace('"', '""') for col in line.split('|')]
            csv_row = ','.join(f'"{col}"' if ',' in col else col for col in row)
            csv_lines.append(csv_row)
    
    if csv_lines:
        return "\n".join(csv_lines).encode('utf-8')
    return text.encode('utf-8')

# --- CSS INJECTION (MINIMAL, GREY FOCUS, SEAMLESS BOTTOM) ---
def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root { 
            --main-bg: #f9fafb; 
            --main-text: #111827; 
            --border-light: #e5e7eb;
            --accent-blue: #0b57d0;
            --focus-grey: #9ca3af; /* Soft grey for the text box */
            
            --sidebar-bg: #0b1020; 
            --sidebar-border: #27314a;
            --sidebar-text: #e8ecf7;
        }
        
        /* Main App Background & Text */
        .stApp { background-color: var(--main-bg); color: var(--main-text); }
        h1, h2, h3, h4, p, span, label, div { color: var(--main-text); }
        .app-subtitle { color: #6b7280 !important; margin-top: -0.25rem; margin-bottom: 2rem; font-size: 0.95rem; }
        
        /* Top Navbar (Share & 3 Dots) - Make Icons White */
        header[data-testid="stHeader"] {
            background-color: var(--sidebar-bg) !important;
        }
        header[data-testid="stHeader"] button, 
        header[data-testid="stHeader"] svg,
        header[data-testid="stHeader"] span {
            color: #ffffff !important;
            fill: #ffffff !important;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: var(--sidebar-bg) !important;
            border-right: 1px solid var(--sidebar-border) !important;
        }
        [data-testid="stSidebar"] * {
            color: var(--sidebar-text) !important;
        }
        
        /* Sidebar Dropdowns & Inputs */
        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] div[data-testid="stTextInput"] input {
            background-color: #12182b !important;
            border-color: var(--sidebar-border) !important;
            color: var(--sidebar-text) !important;
            border-radius: 8px;
        }
        
        /* Sidebar Button (Clear Chat) */
        [data-testid="stSidebar"] div[data-testid="stButton"] button {
            background-color: transparent !important;
            border: 1px solid var(--sidebar-border) !important;
            color: var(--sidebar-text) !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
            border-color: #ef4444 !important;
            color: #ef4444 !important;
        }

        /* Seamless Bottom Chat Background (Aggressive Override) */
        div[data-testid="stBottom"], 
        div[data-testid="stBottom"] > div,
        div[data-testid="stBottom"] > div > div {
            background-color: var(--main-bg) !important;
            background: var(--main-bg) !important;
        }

        /* Chat Input Box - Clean White Pill with Soft Grey Focus */
        div[data-testid="stChatInputContainer"] {
            background-color: #ffffff !important;
            border: 1px solid var(--border-light) !important;
            border-radius: 24px !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important;
            padding: 0.2rem 0.5rem;
        }
        div[data-testid="stChatInputContainer"]:focus-within {
            border-color: var(--focus-grey) !important;
            box-shadow: 0 0 0 1px var(--focus-grey) !important;
            outline: none !important;
        }

        /* Main Area Buttons (FAQ Prompts) - Gemini Style */
        .main div[data-testid="stButton"] button {
            background-color: #f0f4f9 !important;
            border: none !important; 
            color: #1f1f1f !important;
            border-radius: 20px !important; 
            font-weight: 400 !important;
            padding: 0.5rem 1rem !important;
        }
        .main div[data-testid="stButton"] button:hover {
            background-color: #e1e5ea !important;
            color: var(--accent-blue) !important;
        }
        
        /* Download Button Styling */
        .stDownloadButton button {
            background-color: #ffffff !important;
            border: 1px solid var(--border-light) !important;
            border-radius: 8px !important;
            color: var(--main-text) !important;
        }
        .stDownloadButton button:hover {
            border-color: var(--focus-grey) !important;
            background-color: #f9fafb !important;
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

# --- SIDEBAR (Reorganized for Gemini UX) ---
with st.sidebar:
    selected_model = st.selectbox("Model", list(AVAILABLE_MODELS.keys()), index=0, label_visibility="collapsed")
    st.text_input("Search", placeholder="🔍 Search threads...", label_visibility="collapsed")
    
    st.divider()
    
    st.markdown("### Quick Filters")
    donor_status = st.selectbox("Donor Status", ["All", "Active", "Lapsed", "Prospect"])
    state_filter = st.selectbox("State", ["All", "VA", "NY", "CA", "TX"])
    
    for _ in range(8):
        st.write("")
        
    st.divider()
    
    st.markdown("<h4 style='font-size: 14px; font-weight: normal; color: #9aa4bf;'>Settings</h4>", unsafe_allow_html=True)
    
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

# --- FAQ STARTER PROMPTS ---
if not st.session_state.messages:
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏆 Who are the top 10 donors by lifetime donating?"):
            st.session_state.pending_prompt = "Who are the top 10 donors by lifetime donating?"
            st.rerun()
        if st.button("📊 Can you provide a summary of our donating statistics?"):
            st.session_state.pending_prompt = "Can you provide a summary of our donating statistics?"
            st.rerun()
    with col2:
        if st.button("⚠️ Show me lapsed donors who haven't donated since 2023"):
            st.session_state.pending_prompt = "Show me lapsed donors who haven't donated since 2023."
            st.rerun()
        if st.button("🗺️ Show me the geographic distribution of our donors"):
            st.session_state.pending_prompt = "Show me the geographic distribution of our donors."
            st.rerun()

# --- RENDER MESSAGES & DOWNLOAD BUTTONS ---
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            csv_data = convert_to_csv(message["content"])
            is_csv = b',' in csv_data and b'\n' in csv_data
            file_ext = "csv" if is_csv else "txt"
            mime_type = "text/csv" if is_csv else "text/plain"
            
            # Replaced the emoji with a classic arrow
            st.download_button(
                label="⬇ Download Data",
                data=csv_data,
                file_name=f"iasc_data_export_{idx}.{file_ext}",
                mime=mime_type,
                key=f"dl_btn_{idx}"
            )

# --- CHAT INPUT & FILE UPLOADER ---
try:
    prompt_input = st.chat_input("Ask about your donor community...", accept_file=True)
except TypeError:
    prompt_input = st.chat_input("Ask about your donor community...")

active_prompt = None
uploaded_file = None

if prompt_input:
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
        
        tracker_placeholder.markdown(st.session_state.tracker.format_sidebar())
        st.rerun()
