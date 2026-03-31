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
    if csv_lines:
        return "\n".join(csv_lines).encode('utf-8')
    return text.encode('utf-8')

# --- BULLETPROOF CSS INJECTION ---
def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root { 
            --main-bg: #ffffff; 
            --main-text: #111827; 
            --border-light: #e5e7eb;
            --sidebar-bg: #0b1020; 
            --sidebar-border: #27314a;
            --sidebar-text: #ffffff;
        }
        
        [data-testid="stAppViewContainer"] { background-color: var(--main-bg) !important; }
        [data-testid="stAppViewContainer"] h1, 
        [data-testid="stAppViewContainer"] h2, 
        [data-testid="stAppViewContainer"] h3 { color: var(--main-text) !important; }
        .app-subtitle { color: #6b7280 !important; margin-top: -0.25rem; margin-bottom: 2rem; font-size: 0.95rem; }

        /* Assistant Bubbles */
        [data-testid="stChatMessageAvatar"] { display: none !important; }
        [data-testid="stChatMessage"] > div:first-child { display: none !important; width: 0px !important; margin: 0px !important; }
        [data-testid="stChatMessage"] {
            background-color: #f0f4f9 !important;
            border-radius: 20px 20px 20px 4px !important;
            padding: 15px 20px !important;
            margin-bottom: 15px !important;
            width: fit-content !important;
            max-width: 85% !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }
        [data-testid="stChatMessageContent"], [data-testid="stChatMessageContent"] p { color: var(--main-text) !important; }
        [data-testid="stChatMessageContent"] table { color: var(--main-text) !important; border-collapse: collapse; }
        [data-testid="stChatMessageContent"] th, [data-testid="stChatMessageContent"] td { border: 1px solid #d1d5db !important; }

        /* Sidebar Styling */
        [data-testid="stSidebar"] { background-color: var(--sidebar-bg) !important; border-right: 1px solid var(--sidebar-border) !important; }
        [data-testid="stSidebar"] * { color: var(--sidebar-text) !important; }
        [data-testid="stSidebar"] div[data-baseweb="select"] > div { background-color: #12182b !important; border: 1px solid var(--sidebar-border) !important; }

        /* Chat Input Box */
        div[data-testid="stChatInputContainer"] {
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 24px !important;
            padding: 5px 15px !important;
        }

        /* FAQ Buttons */
        [data-testid="stAppViewContainer"] div[data-testid="stButton"] button {
            background-color: #f4f6f8 !important;
            border: none !important;
            border-radius: 20px !important;
            padding: 10px 20px !important;
        }
        [data-testid="stAppViewContainer"] div[data-testid="stButton"] button p { color: #1f1f1f !important; font-weight: 400 !important; }
        [data-testid="stAppViewContainer"] div[data-testid="stButton"] button:hover { background-color: #e8f0fe !important; }
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

# --- SIDEBAR (ONLY SETTINGS AND USAGE, NO FILTERS) ---
with st.sidebar:
    st.markdown("### System Settings")
    selected_model = st.selectbox("Model", list(AVAILABLE_MODELS.keys()), index=0, label_visibility="collapsed")
    st.divider()
    
    st.markdown("### Session Usage")
    tracker_placeholder = st.empty()
    try:
        tracker_placeholder.markdown(st.session_state.tracker.format_sidebar())
    except Exception:
        pass 
        
    st.write("") 
    if st.button("Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.tracker = SessionTracker()
        st.rerun()

# --- MAIN UI ---
st.title(APP_TITLE)
st.markdown(f'<p class="app-subtitle">{APP_SUBTITLE}</p>', unsafe_allow_html=True)

# --- FAQ STARTER PROMPTS (Replaces Quick Filters) ---
if not st.session_state.messages:
    st.markdown("#### How can I help you analyze the donor database?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏆 Top 10 donors by lifetime giving"):
            st.session_state.pending_prompt = "Who are the top 10 donors by lifetime donating?"
            st.rerun()
        if st.button("📊 Summary of donating statistics"):
            st.session_state.pending_prompt = "Can you provide a summary of our donating statistics?"
            st.rerun()
    with col2:
        if st.button("⚠️ Lapsed donors since 2023"):
            st.session_state.pending_prompt = "Show me lapsed donors who haven't donated since 2023."
            st.rerun()
        if st.button("🗺️ Geographic distribution of donors"):
            st.session_state.pending_prompt = "Show me the geographic distribution of our donors."
            st.rerun()

# --- RENDER LOOP ---
for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        st.markdown(
            f"""
            <div style="display: flex; justify-content: flex-end; margin-bottom: 15px;">
                <div style="background-color: #f4f6f8; color: #111827; padding: 12px 18px; border-radius: 20px 20px 4px 20px; max-width: 75%; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    {message["content"]}
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        with st.chat_message("assistant"):
            st.markdown(message["content"])
            
        csv_data = convert_to_csv(message["content"])
        is_csv = b',' in csv_data and b'\n' in csv_data
        if is_csv:
            st.download_button(
                label="📥 Download Data", data=csv_data,
                file_name=f"iasc_data_export_{idx}.csv", mime="text/csv", key=f"dl_btn_{idx}"
            )

# --- CHAT INPUT & EXECUTION ---
active_prompt = None
prompt_input = st.chat_input("Ask about your donor community...")

if prompt_input:
    active_prompt = prompt_input
if st.session_state.pending_prompt:
    active_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if active_prompt:
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    
    st.markdown(
        f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 15px;">
            <div style="background-color: #f4f6f8; color: #111827; padding: 12px 18px; border-radius: 20px 20px 4px 20px; max-width: 75%; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                {active_prompt}
            </div>
        </div>
        """, 
        unsafe_allow_html=True
    )

    with st.status("Consulting IASC records...", expanded=True) as status:
        hidden_instruction = "\n\n[CRITICAL INSTRUCTIONS: 1. Do NOT output 'Tool Call:', 'Results:', or raw JSON. 2. NEVER use the words 'fields', 'columns', 'SQL', or explain your database schema. Do not list internal variable names. 3. Present the final answer conversationally as a human analyst.]"
        enhanced_prompt = active_prompt + hidden_instruction

        raw_response, usage = get_response(
            user_message=enhanced_prompt,
            conversation_history=st.session_state.messages[:-1],
            model=selected_model,
            session_tracker=st.session_state.tracker
        )
        
        clean_response_text = scrub_tool_calls(raw_response)
        status.update(label="Complete!", state="complete", expanded=False)

    st.session_state.messages.append({"role": "assistant", "content": clean_response_text})
    st.rerun()
