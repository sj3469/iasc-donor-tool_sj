"""
IASC Donor Analytics — Streamlit application.
Main entry point: streamlit run src/app.py
"""

import sys
from pathlib import Path
import streamlit as st

# Add src to path for imports so this works regardless of where streamlit is launched
sys.path.insert(0, str(Path(__file__).parent))

from config import APP_TITLE, APP_SUBTITLE, AVAILABLE_MODELS, DEFAULT_MODEL, DB_PATH
from llm import get_response
from token_tracker import SessionTracker
from knowledge import get_knowledge_token_estimate

# ─── Page configuration ───────────────────────────────────────────────────────

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",  # Updated for a professional look
    layout="wide",
)

# ─── Session state initialization ─────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

if "tracker" not in st.session_state:
    st.session_state.tracker = SessionTracker()

if "selected_model" not in st.session_state:
    st.session_state.selected_model = DEFAULT_MODEL

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())[:8]

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    # Branding Section
    st.title(f"📊 {APP_TITLE}")
    st.caption(APP_SUBTITLE)
    st.divider()

    # Key Performance Indicators (KPIs)
    st.subheader("Organizational Overview")
    if DB_PATH.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Enhanced SQL for more expert metrics
            stats = cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN donor_status = 'active' THEN 1 END) as active,
                    COUNT(CASE WHEN donor_status = 'lapsed' THEN 1 END) as lybunt,
                    COUNT(CASE WHEN donor_status = 'prospect' THEN 1 END) as prospects,
                    ROUND(SUM(COALESCE(total_gifts, 0)), 0) as total_giving,
                    ROUND(AVG(email_open_rate) * 100, 1) as avg_engagement
                FROM contacts
            """).fetchone()
            conn.close()

            # High-Level Metrics in a 2x2 Grid
            m_col1, m_col2 = st.columns(2)
            m_col1.metric("Total Contacts", f"{stats['total']:,}")
            m_col2.metric("Total Giving", f"${stats['total_giving']:,.0f}")
            
            m_col3, m_col4 = st.columns(2)
            m_col3.metric("Active Donors", stats['active'])
            m_col4.metric("LYBUNTs", stats['lybunt'], delta="-Lapsed", delta_color="inverse")
            
            st.progress(stats['avg_engagement'] / 100, text=f"Email Engagement: {stats['avg_engagement']}%")

        except Exception as e:
            st.error(f"Data Load Error: {e}")
    else:
        st.warning("Database not found. Run: `python data/generate_mock_data.py`")
    
    st.divider()

    # Interactive Tools
    with st.expander("💡 Sample Questions", expanded=False):
        sample_questions = [
            "Who are our top 10 donors by lifetime giving?",
            "Which lapsed donors in Virginia should we re-engage?",
            "Plan a fundraising trip to NYC: who should we meet?",
            "How many subscribers have never donated but have high wealth scores?",
            "What does our donor pipeline look like?",
            "Show me donors who gave via stock or DAF",
            "What are best practices for re-engaging lapsed donors?",
        ]
        for q in sample_questions:
            if st.button(q, key=f"side_{hash(q)}", use_container_width=True):
                st.session_state.pending_question = q
                st.rerun()

    with st.expander("⚙️ System Settings", expanded=False):
        model_labels = list(AVAILABLE_MODELS.values())
        current_label = AVAILABLE_MODELS.get(st.session_state.selected_model, model_labels[0])
        selected_label = st.selectbox("Model Engine", options=model_labels, index=model_labels.index(current_label))
        
        for m_id, label in AVAILABLE_MODELS.items():
            if label == selected_label:
                st.session_state.selected_model = m_id
                break
        
        st.caption(f"Knowledge Base: ~{get_knowledge_token_estimate():,} tokens")

    # Usage & Budget Tracking
    with st.expander("🪙 Session Budget", expanded=True):
        st.markdown(st.session_state.tracker.format_sidebar())
        team_budget = 500.00
        current_cost = st.session_state.tracker.total_cost
        st.write(f"Team Budget Used: ${current_cost:.4f} / ${team_budget}")
        st.progress(min(current_cost / team_budget, 1.0))

    if st.button("🗑️ Clear Conversation", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.session_state.tracker = SessionTracker()
        st.rerun()

# ─── Main chat area ────────────────────────────────────────────────────────────

st.header(APP_TITLE)
st.caption(APP_SUBTITLE)

# Render the full conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("usage") is not None:
            st.caption(msg["usage"].format_inline(st.session_state.selected_model))

# ─── Input handling ────────────────────────────────────────────────────────────

user_input = st.chat_input("Ask a question about your donors...")

if st.session_state.pending_question and not user_input:
    user_input = st.session_state.pending_question
    st.session_state.pending_question = None

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input, "usage": None})

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ]

    with st.chat_message("assistant"):
        with st.status("Working on your question...", expanded=True) as status:
            try:
                response_text, response_usage = get_response(
                    user_message=user_input,
                    conversation_history=history,
                    model=st.session_state.selected_model,
                    session_tracker=st.session_state.tracker,
                    progress_callback=lambda msg: status.update(label=msg),
                    st_session_id=st.session_state.session_id,
                )
                status.update(label="Done", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Error", state="error", expanded=False)
                response_text = f"**Error:** {e}\n\nPlease check your API configuration."
                response_usage = None

        st.markdown(response_text)
        if response_usage is not None:
            st.caption(response_usage.format_inline(st.session_state.selected_model))

    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "usage": response_usage,
    })
