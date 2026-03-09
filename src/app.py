import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

from config import (
    APP_TITLE,
    APP_SUBTITLE,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    SESSION_BUDGET_USD,
    THREAD_STORE_PATH,
)
from llm import get_response
from queries import get_summary_statistics
from token_tracker import SessionTracker


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="●",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #f7f8fb;
            --panel: #ffffff;
            --panel-2: #f8f9fc;
            --border: #d8deea;
            --text: #172033;
            --muted: #65708a;
            --accent: #24324a;
            --accent-hover: #1c273b;
            --chip: #eef2f8;
            --sidebar-bg: #0f1728;
            --sidebar-border: #25324a;
            --sidebar-text: #ffffff;
            --sidebar-muted: #eef3ff;
            --sidebar-line: #e8edf7;
            --navy: #0f1728;
            --soft-line: #e8edf7;
        }

        html, body, [class*="css"] {
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        .stApp > header {
            background: #ffffff !important;
        }

        header[data-testid="stHeader"] {
            background: #ffffff !important;
            border-bottom: 1px solid var(--soft-line) !important;
        }

        [data-testid="stHeader"] * {
            color: var(--navy) !important;
            fill: var(--navy) !important;
        }

        [data-testid="stToolbar"] * {
            color: var(--navy) !important;
            fill: var(--navy) !important;
        }

        [data-testid="stDecoration"] {
            background: #ffffff !important;
        }

        button[kind="header"] {
            color: var(--navy) !important;
        }

        button[kind="header"] svg {
            fill: var(--navy) !important;
        }

        [data-testid="stSidebar"] {
            background: var(--sidebar-bg) !important;
            border-right: 1px solid var(--sidebar-border);
        }

        [data-testid="stSidebar"] * {
            color: var(--sidebar-text) !important;
        }

        [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"] small,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div {
            color: var(--sidebar-text) !important;
        }

        [data-testid="stSidebar"] input::placeholder,
        [data-testid="stSidebar"] textarea::placeholder {
            color: var(--sidebar-text) !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] hr {
            border: none !important;
            border-top: 1px solid var(--sidebar-line) !important;
        }

        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 5rem;
            max-width: 980px;
        }

        h1, h2, h3, h4, h5, h6, p, span, label, div {
            color: var(--text);
        }

        .app-subtitle {
            color: var(--muted);
            margin-top: -0.2rem;
            margin-bottom: 1rem;
            font-size: 0.98rem;
        }

        .thread-heading {
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 0.2rem;
        }

        .thread-meta {
            color: var(--muted);
            font-size: 0.84rem;
            margin-bottom: 1rem;
        }

        div[data-testid="stTextInput"] input,
        textarea,
        input,
        div[data-baseweb="select"] > div {
            background: var(--panel) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            box-shadow: none !important;
        }

        [data-testid="stSidebar"] div[data-testid="stTextInput"] input,
        [data-testid="stSidebar"] div[data-baseweb="select"] > div {
            background: #162033 !important;
            color: var(--sidebar-text) !important;
            border: 1px solid #31415f !important;
        }

        div[data-testid="stTextInput"] input:focus,
        textarea:focus,
        input:focus {
            border: 1px solid #9aa8c6 !important;
            box-shadow: 0 0 0 1px #9aa8c6 !important;
            outline: none !important;
        }

        [data-testid="stSidebar"] div[data-testid="stTextInput"] input:focus,
        [data-testid="stSidebar"] textarea:focus,
        [data-testid="stSidebar"] input:focus {
            border: 1px solid #5e7398 !important;
            box-shadow: 0 0 0 1px #5e7398 !important;
            outline: none !important;
        }

        div[data-testid="stButton"] button {
            background: var(--accent) !important;
            color: white !important;
            border: 1px solid var(--accent) !important;
            border-radius: 12px !important;
        }

        div[data-testid="stButton"] button:hover {
            background: var(--accent-hover) !important;
            border-color: var(--accent-hover) !important;
        }

        div[data-testid="stChatInput"] {
            background: transparent !important;
        }

        div[data-testid="stChatInput"] > div {
            background: var(--panel) !important;
            border: 1px solid transparent !important;
            border-radius: 22px !important;
            box-shadow: none !important;
        }

        div[data-testid="stChatInput"] > div:focus-within {
            border: 1px solid transparent !important;
            box-shadow: none !important;
        }

        div[data-testid="stChatInput"] textarea {
            color: var(--text) !important;
            background: transparent !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }

        div[data-testid="stChatInput"] textarea::placeholder {
            color: #6c7892 !important;
            opacity: 1 !important;
        }

        div[data-testid="stChatInput"] textarea:focus {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }

        .usage-box {
            border: 1px solid #31415f;
            border-radius: 14px;
            padding: 0.9rem 1rem;
            background: #162033;
            color: var(--sidebar-text);
        }

        .usage-box div {
            color: var(--sidebar-text) !important;
        }

        .model-chip {
            display: inline-block;
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 0.32rem 0.7rem;
            font-size: 0.82rem;
            color: var(--text);
            background: var(--chip);
            margin-bottom: 0.75rem;
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            background: var(--panel) !important;
        }

        [data-testid="stSidebar"] [data-testid="stExpander"] {
            border: 1px solid #31415f !important;
            background: #162033 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def make_thread(title: str = "New thread") -> dict:
    ts = now_iso()
    return {
        "id": uuid.uuid4().hex,
        "title": title,
        "created_at": ts,
        "updated_at": ts,
        "messages": [],
    }


def load_threads() -> list[dict]:
    path = Path(THREAD_STORE_PATH)
    if not path.exists():
        return [make_thread()]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            return data
    except Exception:
        pass

    return [make_thread()]


def save_threads(threads: list[dict]) -> None:
    Path(THREAD_STORE_PATH).write_text(
        json.dumps(threads, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def ensure_state() -> None:
    if "threads" not in st.session_state:
        st.session_state.threads = load_threads()
    if "active_thread_id" not in st.session_state:
        st.session_state.active_thread_id = st.session_state.threads[0]["id"]
    if "tracker" not in st.session_state:
        st.session_state.tracker = SessionTracker()
    if "thread_search" not in st.session_state:
        st.session_state.thread_search = ""
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = DEFAULT_MODEL


def get_active_thread() -> dict:
    for thread in st.session_state.threads:
        if thread["id"] == st.session_state.active_thread_id:
            return thread

    thread = make_thread()
    st.session_state.threads.insert(0, thread)
    st.session_state.active_thread_id = thread["id"]
    save_threads(st.session_state.threads)
    return thread


def format_thread_title(prompt: str) -> str:
    cleaned = re.sub(r"\s+", " ", prompt).strip()
    if not cleaned:
        return "New thread"
    words = cleaned.split()
    title = " ".join(words[:7])
    if len(words) > 7:
        title += "…"
    return title


def thread_matches_search(thread: dict, query: str) -> bool:
    if not query:
        return True
    q = query.lower().strip()
    if q in thread.get("title", "").lower():
        return True
    for message in thread.get("messages", []):
        if q in message.get("content", "").lower():
            return True
    return False


def create_new_thread() -> None:
    thread = make_thread()
    st.session_state.threads.insert(0, thread)
    st.session_state.active_thread_id = thread["id"]
    save_threads(st.session_state.threads)


def add_message(role: str, content: str, attachments: list[str] | None = None) -> None:
    thread = get_active_thread()
    thread["messages"].append(
        {
            "role": role,
            "content": content,
            "attachments": attachments or [],
            "timestamp": now_iso(),
        }
    )
    thread["updated_at"] = now_iso()

    if role == "user":
        user_count = len([m for m in thread["messages"] if m["role"] == "user"])
        if user_count == 1:
            thread["title"] = format_thread_title(content)

    save_threads(st.session_state.threads)


def get_state_options() -> list[str]:
    fallback = [
        "All", "VA", "NY", "DC", "MD", "MA", "IL", "CA", "TX", "FL",
        "PA", "OH", "GA", "NC", "WA", "CO", "MN", "MO", "AZ", "TN", "NJ"
    ]
    try:
        result = get_summary_statistics(group_by="state")
        rows = result.get("results", [])
        states = sorted([r.get("group_value") for r in rows if r.get("group_value")])
        return ["All"] + states if states else fallback
    except Exception:
        return fallback


def build_effective_prompt(prompt: str, donor_status_filter: str, state_filter: str) -> str:
    notes = []
    if donor_status_filter != "All":
        notes.append(f"donor_status = {donor_status_filter}")
    if state_filter != "All":
        notes.append(f"state = {state_filter}")

    if not notes:
        return prompt

    return (
        "Apply these sidebar filters unless the user explicitly overrides them:\n- "
        + "\n- ".join(notes)
        + "\n\nUser question:\n"
        + prompt
    )


def render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.text(message["content"])
        else:
            st.markdown(message["content"])
            attachments = message.get("attachments") or []
            if attachments:
                st.caption("Attached: " + ", ".join(attachments))


def session_spend_and_remaining() -> tuple[float, float]:
    spent = getattr(st.session_state.tracker, "total_cost", 0.0) or 0.0
    remaining = max(0.0, SESSION_BUDGET_USD - spent)
    return spent, remaining


def parse_chat_submission(submission) -> tuple[str, list]:
    if submission is None:
        return "", []

    if isinstance(submission, str):
        return submission.strip(), []

    text = ""
    files = []

    try:
        text = submission.text or ""
    except Exception:
        try:
            text = submission.get("text", "")
        except Exception:
            text = ""

    try:
        files = list(submission.files or [])
    except Exception:
        try:
            files = list(submission.get("files", []) or [])
        except Exception:
            files = []

    return text.strip(), files


ensure_state()
inject_css()
state_options = get_state_options()

with st.sidebar:
    selected_model = st.selectbox(
        "Model",
        list(AVAILABLE_MODELS.keys()),
        format_func=lambda x: AVAILABLE_MODELS[x],
        index=list(AVAILABLE_MODELS.keys()).index(
            st.session_state.get("selected_model", DEFAULT_MODEL)
        ),
    )
    st.session_state.selected_model = selected_model

    st.text_input(
        "Search threads",
        key="thread_search",
        placeholder="Search threads",
        label_visibility="collapsed",
    )

    if st.button("+ New thread", use_container_width=True):
        create_new_thread()
        st.rerun()

    st.markdown("#### History")
    sorted_threads = sorted(
        st.session_state.threads,
        key=lambda t: t.get("updated_at", ""),
        reverse=True,
    )

    history_threads = [t for t in sorted_threads if t.get("messages")]
    visible_threads = [
        t for t in history_threads
        if thread_matches_search(t, st.session_state.thread_search)
    ]

    if not visible_threads:
        st.caption("No matching threads")
    else:
        for thread_item in visible_threads:
            label = thread_item["title"] or "Untitled thread"
            prefix = "• " if thread_item["id"] == st.session_state.active_thread_id else ""
            if st.button(f"{prefix}{label}", key=f"thread_{thread_item['id']}", use_container_width=True):
                st.session_state.active_thread_id = thread_item["id"]
                st.rerun()

    st.divider()

    st.markdown("#### Quick filters")
    donor_status_filter = st.selectbox(
        "Donor status",
        ["All", "active", "lapsed", "prospect", "new_donor"],
        index=0,
    )
    state_filter = st.selectbox(
        "State",
        state_options,
        index=0,
    )
