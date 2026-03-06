import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# 1. Load local .env for local testing
load_dotenv()

# 2. Key Title & Text
APP_TITLE = "IASC Donor Analytics"
APP_SUBTITLE = "AI-powered donor intelligence for the IASC and The Hedgehog Review"

# 3. Path Configurations
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "donors.db"

# 4. API Key Resolution (Web vs Local)
# This logic checks Streamlit Secrets first (Web), then environment variables (Local)
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

# 5. Model Settings
AVAILABLE_MODELS = {
    "gemini-2.0-flash": "Gemini 2.0 Flash (Fastest)",
    "gemini-1.5-pro": "Gemini 1.5 Pro (Most Capable)",
    "claude-3-5-sonnet-20240620": "Claude 3.5 Sonnet",
}
DEFAULT_MODEL = "gemini-2.0-flash"

# Inject keys into environment so the clients can find them automatically
if GEMINI_API_KEY:
    os.environ[AIzaSyAwNhYgYsyPfn15l4I8gF8T6Z-ukMfpaCA] = GEMINI_API_KEY
