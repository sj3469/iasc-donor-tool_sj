import os
import re
import time
from types import SimpleNamespace
from typing import List, Dict, Any, Optional, Callable

from google import genai
from google.genai import types

from prompts import build_system_prompt
from queries import (
    search_donors,
    get_donor_detail,
    get_summary_statistics,
    get_geographic_distribution,
    get_lapsed_donors,
    get_prospects_by_potential,
)


def _build_prompt_content(user_message: str, conversation_history: List[Dict[str, str]]) -> str:
    parts = []
    for msg in conversation_history[-10:]:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        if content:
            parts.append(f"{role}: {content}")
    parts.append(f"User: {user_message}")
    return "\n".join(parts)


def _extract_response_text(response: Any) -> str:
    try:
        if response.text and str(response.text).strip():
            return str(response.text).strip()
    except Exception:
        pass

    texts = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", []) or []
        for part in parts:
            text = getattr(part, "text", None)
            if text and str(text).strip():
                texts.append(str(text).strip())

    return "\n".join(texts).strip() if texts else "No response text returned."


def _fmt_currency(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return str(value)


def _format_donor_list(title: str, result: dict) -> str:
    rows = result.get("results", []) or []
    if not rows:
        return f"{title}\n\nNo matching donors found."

    lines = [title, ""]
    for i, row in enumerate(rows[:10], start=1):
        lines.append(
            f"{i}. {row.get('Contact ID', 'Unknown ID')} | ZIP {row.get('Mailing Zip/Postal Code', 'N/A')} | "
            f"Total gifts {_fmt_currency(row.get('Total Gifts', 0))} | "
            f"Last gift {row.get('Last Gift Date', 'N/A')} | "
            f"Status {row.get('donor_status', 'N/A')} | "
            f"Wealth {row.get('wealth_score', 'N/A')}"
        )
    return "\n".join(lines)


def get_response(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    model: str,
    session_tracker: Any,
    progress_callback: Optional[Callable[[str], None]] = None,
    st_session_id: Optional[str] = None,
    attachment: Optional[Any] = None,
) -> tuple[str, Any]:
    start = time.perf_counter()
    msg = user_message.lower().strip()

    zip_match = re.search(r"\b(\d{5})\b", user_message)

    if "state" in msg:
        response_text = (
            "This dataset does not include a state field. "
            "I can show top donors overall, top donors in a ZIP/postal code, lapsed donors, "
            "or top prospects by wealth score."
        )
        usage = SimpleNamespace(prompt_token_count=0, candidates_token_count=0)
    elif ("top donors" in msg or "show donors" in msg) and zip_match:
        result = search_donors(zip_code=zip_match.group(1), sort_by="total_gifts", sort_order="desc", limit=10)
        response_text = _format_donor_list(f"Top donors in ZIP {zip_match.group(1)}", result)
        usage = SimpleNamespace(prompt_token_count=0, candidates_token_count=0)
    elif "top donors" in msg or "show top donors" in msg:
        result = search_donors(sort_by="total_gifts", sort_order="desc", limit=10)
        response_text = _format_donor_list("Top donors overall", result)
        usage = SimpleNamespace(prompt_token_count=0, candidates_token_count=0)
    elif "lapsed donors" in msg:
        result = get_lapsed_donors(limit=10)
        response_text = _format_donor_list("Top lapsed donors", result)
        usage = SimpleNamespace(prompt_token_count=0, candidates_token_count=0)
    elif "prospects" in msg and ("top" in msg or "wealth" in msg):
        result = get_prospects_by_potential(limit=10)
        response_text = _format_donor_list("Top prospects by wealth score", result)
        usage = SimpleNamespace(prompt_token_count=0, candidates_token_count=0)
    elif "summary" in msg or "statistics" in msg:
        result = get_summary_statistics()
        row = (result.get("results") or [{}])[0]
        response_text = (
            f"Donor count: {row.get('donor_count', 0)}\n"
            f"Total giving: {_fmt_currency(row.get('total_giving', 0))}\n"
            f"Average total giving: {_fmt_currency(row.get('avg_total_giving', 0))}\n"
            f"Average gift: {_fmt_currency(row.get('avg_gift', 0))}\n"
            f"Average wealth score: {row.get('avg_wealth_score', 0)}"
        )
        usage = SimpleNamespace(prompt_token_count=0, candidates_token_count=0)
    else:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        raw_prompt = build_system_prompt()
        if isinstance(raw_prompt, list):
            system_instruction_text = " ".join(
                p.get("text", "") if isinstance(p, dict) else str(p) for p in raw_prompt
            )
        else:
            system_instruction_text = str(raw_prompt)

        prompt_content = _build_prompt_content(user_message, conversation_history)

        response = client.models.generate_content(
            model=model,
            contents=prompt_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction_text,
                temperature=0.2,
            ),
        )
        usage = response.usage_metadata
        response_text = _extract_response_text(response)

    latency_ms = (time.perf_counter() - start) * 1000
    session_tracker.log_call(
        model=model,
        input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
        output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        latency_ms=latency_ms,
        question=user_message,
    )

    return response_text, usage

