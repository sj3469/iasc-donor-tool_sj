import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# 1. Load local .env for local testing
load_dotenv()

# 2. Page Metadata
APP_TITLE = "IASC Donor Analytics"
APP_SUBTITLE = "AI-powered donor intelligence for the IASC and The Hedgehog Review"

# 3. Path Configurations [FIXED FOR YOUR SRC STRUCTURE]
# Since mock_dataset3.csv is inside 'src', we point directly to it
BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "mock_dataset3.csv"
DB_PATH = BASE_DIR / "donors.db"

# API configuration
try:
    import streamlit as st
    ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
except Exception:
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Model configuration
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
AVAILABLE_MODELS = {
    "gemini-2.0-flash": "Gemini 2.0 Flash (Fastest)",
    "gemini-1.5-pro": "Gemini 1.5 Pro (Most Capable)",
}
DEFAULT_MODEL = "gemini-2.0-flash"

# 6. Inject key into environment safely
if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
