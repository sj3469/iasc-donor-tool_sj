import os
import sys
import re
import inspect
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
from llm import get_response, scrub_tool_calls
from token_tracker import SessionTracker

APP_TITLE = getattr(config, "APP_TITLE", "IASC Donor Analytics")
APP_SUBTITLE = getattr(config, "APP_SUBTITLE", "AI-powered donor intelligence")
AVAILABLE_MODELS = getattr(config, "AVAILABLE_MODELS", {"gemini-2.0-flash": "Gemini 2.0 Flash"})

# --- PAGE CONFIG ---
st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# --- CSS: REMOVING ALL LEGACY FILTER STYLING ---
def inject_css() -> None:
    st.markdown(
        """
        <style>
        /* Sidebar Styling */
        [data-testid="stSidebar"] { background-color: #0b1020 !important; min-width: 280px !important; }
        [data-testid="stSidebar"] * { color: #ffffff !important; }
        
        /* Chat Bubble Styling */
        .stChatMessage { border-radius: 15px !important; margin-bottom: 10px !important; }
        
        /* Starter Prompt Buttons (Pills) */
        .stButton button {
            border-radius: 20px !important;
            padding: 10px 20px !important;
            border: 1px solid #e5e7eb !important;
            color: #1f2937 !important;
            background-color: #f9fafb !important;
        }
        .stButton button:hover { border-color: #0b57d0 !important; color: #0b57d0 !important; }
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

# --- SIDEBAR: STRICTLY SYSTEM ONLY (NO FILTERS) ---
with st.sidebar:
    st.subheader("Settings")
    selected_model = st.selectbox("Intelligence Engine", list(AVAILABLE_MODELS.keys()), index=0)
    
    st.divider()
    st.subheader("Usage Metrics")
    st.markdown(st.session_state.tracker.format_sidebar())
    
    st.write("") 
    if st.button("Reset Session", use_container_width=True):
        st.session_state.messages = []
        st.session_state.tracker = SessionTracker()
        st.rerun()

# --- MAIN UI ---
st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

# --- CHAT RENDERING ---
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- CONTEXTUAL UI: STARTER PROMPTS ---
# Only visible when no messages exist to prevent cluttering the conversational flow
if not st.session_state.messages:
    st.write("### How can I help you today?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏆 List the top 10 donors overall"):
            st.session_state.pending_prompt = "Who are the top 10 donors by lifetime giving?"
            st.rerun()
        if st.button("🗺️ Show donor distribution by state"):
            st.session_state.pending_prompt = "Provide a summary of donors by state."
            st.rerun()
    with col2:
        if st.button("⏳ Find lapsed donors (Pre-2023)"):
            st.session_state.pending_prompt = "Show me lapsed donors who haven't donated since 2023."
            st.rerun()
        if st.button("📊 Database Summary Statistics"):
            st.session_state.pending_prompt = "Provide a high-level summary of our donor database statistics."
            st.rerun()

# --- CHAT INPUT ---
prompt = st.chat_input("Ask a question about your donor base...")

# Trigger processing if user types OR clicks a starter prompt
active_input = prompt or st.session_state.pending_prompt

if active_input:
    # Clear the pending prompt immediately
    st.session_state.pending_prompt = None
    
    # Add User Message to History
    st.session_state.messages.append({"role": "user", "content": active_input})
    with st.chat_message("user"):
        st.markdown(active_input)

    # Process Response
    with st.status("Analyzing records...") as status:
        # We pass the selected_model from the sidebar here
        response, usage = get_response(
            user_message=active_input,
            conversation_history=st.session_state.messages[:-1],
            model=selected_model,
            session_tracker=st.session_state.tracker
        )
        
        clean_text = scrub_tool_calls(response)
        status.update(label="Complete", state="complete", expanded=False)

    # Add Assistant Message to History
    st.session_state.messages.append({"role": "assistant", "content": clean_text})
    st.rerun()
