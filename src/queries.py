"""
queries.py — Data query functions for the IASC Donor Analytics tool.
"""

import math
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

# Use the central definition from config to prevent path errors
from config import DB_PATH

def get_db_connection() -> sqlite3.Connection:
    """Open a read-only connection using the shared DB_PATH."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def _rows_to_dicts(rows: list) -> list[dict]:
    return [dict(row) for row in rows]

# --- Keep all your existing functions (search_donors, etc.) below this line ---
# (I am omitting the rest of your functions here to keep this message short, 
# but they should remain exactly as you have them in your file)
