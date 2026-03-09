import streamlit as st
import os
import sys
from pathlib import Path

# Fix for Streamlit Cloud imports
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from config import APP_TITLE, APP_SUBTITLE, AVAILABLE_MODELS, DEFAULT_MODEL
from llm import get_response
from token_tracker import SessionTokenTracker

st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "tracker" not in st.session_state:
    st.session_state.tracker = SessionTokenTracker()

with st.sidebar:
    st.title("⚙️ Settings")
    selected_model = st.selectbox("Select Model", list(AVAILABLE_MODELS.keys()), 
                                  format_func=lambda x: AVAILABLE_MODELS[x])
    
    st.divider()
    # This displays the stats from your token_tracker.py
    st.markdown(st.session_state.tracker.format_sidebar())
    
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

st.title(APP_TITLE)
st.subheader(APP_SUBTITLE)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about your donor community..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        with st.status("Analyzing database...", expanded=True) as status:
            response, usage = get_response(
                user_message=prompt,
                conversation_history=st.session_state.messages[:-1],
                model=selected_model,
                session_tracker=st.session_state.tracker
            )
            status.update(label="Complete!", state="complete", expanded=False)
        
        response_placeholder.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
