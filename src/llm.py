import os
from typing import List, Dict, Any, Optional, Callable
from google import genai
from google.genai import types

from queries import (
    search_donors, get_donor_detail, get_summary_statistics,
    get_geographic_distribution, get_lapsed_donors,
    get_prospects_by_potential, plan_fundraising_trip
)
from config import AVAILABLE_MODELS
from prompts import build_system_prompt

def get_response(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    model: str,
    session_tracker: Any,
    progress_callback: Optional[Callable[[str], None]] = None,
    st_session_id: Optional[str] = None,
    attachment: Optional[Any] = None
) -> tuple[str, Any]:
    
    # Initialize only the Gemini Client
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    # Register Python functions as tools
    tools = [
        search_donors, get_donor_detail, get_summary_statistics,
        get_geographic_distribution, get_lapsed_donors,
        get_prospects_by_potential, plan_fundraising_trip
    ]

    prompt_content = [user_message]
    
    # Handle photo/file uploads via Gemini Files API
    if attachment:
        if progress_callback: progress_callback(f"Processing {attachment.name}...")
        file_handle = client.files.upload(file=attachment)
        prompt_content.append(file_handle)

    if progress_callback: progress_callback("Querying IASC Database...")

    # Execute with Automatic Function Calling
    response = client.models.generate_content(
        model=model,
        contents=prompt_content,
        config=types.GenerateContentConfig(
            system_instruction=build_system_prompt(),
            tools=tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(max_remote_calls=5)
        )
    )

    usage = response.usage_metadata
    session_tracker.log_call(model=model, input_tokens=usage.prompt_token_count, output_tokens=usage.candidates_token_count)

    return response.text, usage
