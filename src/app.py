"""
IASC Donor Analytics — Expert Gemini-Style UI
Main entry point: streamlit run src/app.py
"""

import sys
import pandas as pd
import sqlite3
from pathlib import Path
import streamlit as st

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import APP_TITLE, APP_SUBTITLE, AVAILABLE_MODELS, DEFAULT_MODEL, DB_PATH
from llm import get_response
from token_tracker import SessionTracker
from knowledge import get_knowledge_token_estimate

# ─── Data Logic: Fix "Database Not Found" ─────────────────────────────────────

def initialize_database():
    """Converts the uploaded CSV to the SQLite DB format the app expects."""
    if not DB_PATH.exists():
        # Look for the specific file you added to GitHub
        csv_path = Path("data/mock_dataset3.csv")
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            conn = sqlite3.connect(DB_PATH)
            # The app logic specifically looks for a table named 'contacts'
            df.to_sql("contacts", conn, index=False, if_exists="replace")
            conn.close()

initialize_database()

# ─── Page configuration ───────────────────────────────────────────────────────

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
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

# ─── Sidebar (Client-Tailored UX) ─────────────────────────────────────────────

with st.sidebar:
    st.title(f"📊 {APP_TITLE}")
    st.caption(APP_SUBTITLE)
    st.divider()

    # Gemini-style File Upload Component
    st.subheader("📎 Attach Files")
    uploaded_file = st.file_uploader(
        "Upload a donor list, report, or image", 
        type=["pdf", "csv", "txt", "png", "jpg"],
        help="Analyzed by Gemini/Claude for this session only."
    )

    st.divider()

    # IASC Client Metrics
    st.subheader("IASC Quick Stats")
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        stats = cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN donor_status = 'active' THEN 1 END) as active,
                COUNT(CASE WHEN donor_status = 'lapsed' THEN 1 END) as lybunt,
                ROUND(SUM(COALESCE(total_gifts, 0)), 0) as total_giving
            FROM contacts
        """).fetchone()
        conn.close()

        m_col1, m_col2 = st.columns(2)
        m_col1.metric("Total Contacts", f"{stats['total']:,}")
        m_col2.metric("Active Donors", stats['active'])
        
        st.metric("Total Lifetime Giving", f"${stats['total_giving']:,.0f}")
        st.caption(f"LYBUNT Count: {stats['lybunt']}")
    except Exception:
        st.info("Statistics will update once the data sync is complete.")

    st.divider()
    
    with st.expander("💡 Sample Questions"):
        questions = [
            "Who are our top 10 donors?", 
            "Plan a fundraising trip to NYC", 
            "Lapsed donor benchmarks"
        ]
        for q in questions:
            if st.button(q, key=f"side_{hash(q)}", use_container_width=True):
                st.session_state.pending_question = q
                st.rerun()

    st.divider()
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.tracker = SessionTracker()
        st.rerun()

# ─── Main Chat Interface (Gemini-Style) ───────────────────────────────────────

st.header(APP_TITLE)
st.caption("AI-powered donor intelligence for the IASC and The Hedgehog Review")

# Render conversation history using Gemini-style chat bubbles
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("usage"):
            st.caption(msg["usage"].format_inline(st.session_state.selected_model))

# Sticky Chat Input at the bottom
user_input = st.chat_input("Ask about your donors or an uploaded file...")

# Handle Sample Question button clicks
if st.session_state.pending_question and not user_input:
    user_input = st.session_state.pending_question
    st.session_state.pending_question = None

if user_input:
    # 1. User Message
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 2. Assistant Response with status indicator
    with st.chat_message("assistant"):
        with st.status("Analyzing IASC data...", expanded=True) as status:
            try:
                # Pass the attachment directly to the LLM logic
                response_text, response_usage = get_response(
                    user_message=user_input,
                    conversation_history=st.session_state.messages[:-1],
                    model=st.session_state.selected_model,
                    session_tracker=st.session_state.tracker,
                    progress_callback=lambda m: status.update(label=m),
                    st_session_id=st.session_state.session_id,
                    attachment=uploaded_file
                )
                status.update(label="Complete", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Error", state="error", expanded=False)
                response_text = f"**Error encountered:** {e}"
                response_usage = None

        st.markdown(response_text)
        
        # Expert UX: CSV Download Button appears if data is returned
        if any(keyword in response_text.lower() for keyword in ["list", "donor", "data"]):
             st.download_button(
                "📥 Export Results to CSV",
                data=response_text,
                file_name="iasc_donor_export.csv",
                mime="text/csv"
             )

        if response_usage:
            st.caption(response_usage.format_inline(st.session_state.selected_model))

    # Persist the history
    st.session_state.messages.append({"role": "assistant", "content": response_text, "usage": response_usage})
