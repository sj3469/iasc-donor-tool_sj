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
# This looks in Streamlit Secrets first (for the web), then your local environment.
GEMINI_API_KEY = st.secrets.get(AIzaSyAwNhYgYsyPfn15l4I8gF8T6Z-ukMfpaCA) or os.getenv(AIzaSyAwNhYgYsyPfn15l4I8gF8T6Z-ukMfpaCA) or "AIzaSyAwNhYgYsyPfn15l4I8gF8T6Z-ukMfpaCA"
ANTHROPIC_API_KEY = st.secrets.get("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") or os.getenv("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") or "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"

# 5. Model Settings
AVAILABLE_MODELS = {
    "gemini-2.0-flash": "Gemini 2.0 Flash (Fastest)",
    "gemini-1.5-pro": "Gemini 1.5 Pro (Most Capable)",
    "claude-3-5-sonnet-20240620": "Claude 3.5 Sonnet",
}
DEFAULT_MODEL = "gemini-2.0-flash"

# 6. Inject keys into environment [CRITICAL FIX]
# Use the string names "GEMINI_API_KEY" so the model knows where to look.
if GEMINI_API_KEY:
    os.environ["AIzaSyAwNhYgYsyPfn15l4I8gF8T6Z-ukMfpaCA"] = GEMINI_API_KEY
if ANTHROPIC_API_KEY:
    os.environ["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"] = ANTHROPIC_API_KEY
