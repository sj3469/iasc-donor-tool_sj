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
SELECTED_MODEL = list(AVAILABLE_MODELS.keys())[0]

# --- PAGE CONFIG ---
st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# --- HELPERS ---
def convert_to_csv(text):
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
    return "\n".join(csv_lines).encode('utf-8') if csv_lines else text.encode('utf-8')

# --- CSS INJECTION (Cleaned up for Conversational Focus) ---
def inject_css() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] { background-color: #ffffff !important; }
        [data-testid="stSidebar"] { background-color: #0b1020 !important; }
        [data-testid="stSidebar"] * { color: #ffffff !important; }
        
        /* User Message Bubble */
        .user-bubble {
            background-color: #f4f6f8;
            color: #111827;
            padding: 12px 18px;
            border-radius: 20px 20px 4px 20px;
            max-width: 75%;
            margin-left: auto;
            margin-bottom: 15px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        /* Suggestion Chips */
        .stButton button {
            border-radius: 20px !important;
            border: 1px solid #d1d5db !important;
            background-color: white !important;
            color: #374151 !important;
        }
        .stButton button:hover {
            border-color: #0b57d0 !important;
            color: #0b57d0 !important;
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

# --- SIDEBAR (MODIFIED: QUICK FILTERS REMOVED) ---
with st.sidebar:
    st.markdown("### System Settings")
    model_choice = st.selectbox("Active Model", list(AVAILABLE_MODELS.keys()), index=0)
    st.divider()
    
    # Display usage stats
    st.markdown(st.session_state.tracker.format_sidebar())
    
    st.write("") 
    if st.button("Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.tracker = SessionTracker()
        st.rerun()

# --- MAIN UI ---
st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

# --- CHAT RENDER LOOP ---
for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        st.markdown(f'<div class="user-bubble">{message["content"]}</div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant"):
            st.markdown(message["content"])
            csv_data = convert_to_csv(message["content"])
            if b',' in csv_data:
                st.download_button("📥 Download Export", data=csv_data, file_name=f"export_{idx}.csv", key=f"dl_{idx}")

# --- SUGGESTION ENGINE (UX REPLACEMENT FOR FILTERS) ---
# Only show these if the chat is empty or just finished a thought
if not st.session_state.messages:
    st.write("How can I help you today?")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🏆 Top 10 Donors"): st.session_state.pending_prompt = "Who are the top 10 donors by lifetime giving?"
    with c2:
        if st.button("⏳ Lapsed (Pre-2023)"): st.session_state.pending_prompt = "Show me lapsed donors who haven't donated since 2023."
    with c3:
        if st.button("🗺️ Geography"): st.session_state.pending_prompt = "Show me the geographic distribution of our supporters."

# --- CHAT INPUT ---
prompt = st.chat_input("Ask a question about the IASC donor base...")

if prompt or st.session_state.pending_prompt:
    active_prompt = prompt if prompt else st.session_state.pending_prompt
    st.session_state.pending_prompt = None
    
    # Add to history
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    
    # Execute
    with st.status("Consulting IASC records...") as status:
        hidden_instruction = "\n\n[Present the final answer conversationally as a human analyst. Do not mention technical fields.]"
        
        response, usage = get_response(
            user_message=active_prompt + hidden_instruction,
            conversation_history=st.session_state.messages[:-1],
            model=model_choice,
            session_tracker=st.session_state.tracker
        )
        
        clean_text = scrub_tool_calls(response)
        status.update(label="Analysis Complete", state="complete", expanded=False)

    st.session_state.messages.append({"role": "assistant", "content": clean_text})
    st.rerun()
