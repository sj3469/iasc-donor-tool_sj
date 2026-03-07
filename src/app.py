import streamlit as st
import os

from config import APP_TITLE, APP_SUBTITLE, AVAILABLE_MODELS, DEFAULT_MODEL
from llm import get_response
from token_tracker import SessionTracker
from usage_store import get_usage_summary




# 1. Page Configuration [Restores your missing titles]
st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide")

# 2. Initialize Session States
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tracker" not in st.session_state:
    st.session_state.tracker = SessionTracker()


with st.sidebar:
    st.title("⚙️ Settings")

    selected_model = st.selectbox(
        "Select Model",
        list(AVAILABLE_MODELS.keys()),
        format_func=lambda x: AVAILABLE_MODELS[x],
        index=list(AVAILABLE_MODELS.keys()).index(DEFAULT_MODEL),
    )

    st.divider()

    st.markdown("### 📁 Data Source")
    st.info("Connected: `mock_dataset3.csv`")

    st.markdown("### 📊 Session Usage")
    st.markdown(st.session_state.tracker.format_sidebar())

    st.markdown("### 🗄️ App Usage")
    try:
        app_usage = get_usage_summary()
        st.caption(f"API calls: {app_usage.get('total_api_calls', 0)}")
        st.caption(f"Sessions: {app_usage.get('total_sessions', 0)}")
        st.caption(f"Input tokens: {app_usage.get('total_input_tokens', 0):,}")
        st.caption(f"Output tokens: {app_usage.get('total_output_tokens', 0):,}")
        st.caption(f"Estimated cost: ${app_usage.get('estimated_total_cost_usd', 0):.4f}")
    except Exception as e:
        st.warning(f"Usage stats unavailable: {e}")

    st.divider()

    st.markdown("### 🎯 Quick Filters")
    donor_status_filter = st.selectbox(
        "Default donor status view",
        ["All", "active", "lapsed", "prospect", "new_donor"],
        index=0,
    )
    sort_choice = st.selectbox(
        "Default ranking",
        ["total_gifts", "last_name", "wealth_score"],
        index=0,
    )

    st.divider()

    st.markdown("### ❓ Frequently Asked Questions")
    with st.expander("What can I ask here?"):
        st.markdown(
            "- Show top donors in a state\n"
            "- Find lapsed donors worth re-engaging\n"
            "- Identify high-potential prospects\n"
            "- Summarize geographic donor distribution\n"
            "- Suggest outreach candidates"
        )

    with st.expander("Why are some answers short?"):
        st.markdown(
            "Some query tools are still basic stubs, so results may be limited "
            "until more query functions are fully implemented."
        )

    with st.expander("Why might usage stats look odd?"):
        st.markdown(
            "Your tracker and usage storage were originally written around a different "
            "pricing setup, so cost estimates may need updating."
        )

    st.divider()

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()


# 4. Main UI Header [Fixes the blank screen issue]
st.title(APP_TITLE)
st.subheader(APP_SUBTITLE)

# 5. Chat Interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about your donor community..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        with st.status("Analyzing IASC database...", expanded=True) as status:
            response, usage = get_response(
                user_message=prompt,
                conversation_history=st.session_state.messages[:-1],
                model=selected_model,
                session_tracker=st.session_state.tracker
            )
            status.update(label="Analysis Complete!", state="complete", expanded=False)
        
        response_placeholder.markdown(response)

        try:
            st.caption(
                f"Model: {selected_model} | "
                f"Prompt tokens: {getattr(usage, 'prompt_token_count', 0)} | "
                f"Output tokens: {getattr(usage, 'candidates_token_count', 0)}"
            )
        except Exception:
            pass
        
        st.session_state.messages.append({"role": "assistant", "content": response})

