"""
Token usage tracker for the IASC donor analytics tool.

Tracks per-response and per-session token usage and estimated costs,
including prompt caching savings. Designed to be displayed inline with
each response and in the Streamlit sidebar.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime


# Pricing as of early 2025; update these if pricing changes.
# Sources: anthropic.com/pricing, openai.com/pricing
MODEL_PRICING = {
    "gpt-5.5-pro": {
        "input_per_mtok": 30.00,
        "output_per_mtok": 180.00,
        "display_name": "GPT-5.5 Pro",
    },
    "gpt-5.5": {
        "input_per_mtok": 5.00,
        "output_per_mtok": 30.00,
        "display_name": "GPT-5.5",
    },
    "gpt-5.4-pro": {
        "input_per_mtok": 30.00,
        "output_per_mtok": 180.00,
        "display_name": "GPT-5.4 Pro",
    },
    "gpt-5.4": {
        "input_per_mtok": 2.50,
        "output_per_mtok": 15.00,
        "display_name": "GPT-5.4",
    },
    "gpt-5.4-mini": {
        "input_per_mtok": 0.75,
        "output_per_mtok": 4.50,
        "display_name": "GPT-5.4 mini",
    },
    "gpt-5.4-nano": {
        "input_per_mtok": 0.20,
        "output_per_mtok": 1.25,
        "display_name": "GPT-5.4 nano",
    },
    "claude-sonnet-4-20250514": {
        "input_per_mtok": 3.00,
        "output_per_mtok": 15.00,
        "display_name": "Claude Sonnet",
    },
    "claude-haiku-4-5-20251001": {
        "input_per_mtok": 0.80,
        "output_per_mtok": 4.00,
        "display_name": "Claude Haiku",
    },
    "gpt-4o": {
        "input_per_mtok": 2.50,
        "output_per_mtok": 10.00,
        "display_name": "GPT-4o",
    },
    "gpt-4o-mini": {
        "input_per_mtok": 0.15,
        "output_per_mtok": 0.60,
        "display_name": "GPT-4o mini",
    },
}


@dataclass
class APICall:
    """A single API call within a response."""
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    model: str
    had_tool_use: bool
    latency_ms: float
    cache_creation_input_tokens: int = 0  # tokens written to cache (charged at 1.25x)
    cache_read_input_tokens: int = 0      # tokens read from cache (charged at 0.1x)


@dataclass
class ResponseUsage:
    """Aggregated usage for one user question (may involve multiple API calls)."""
    question: str
    calls: list = field(default_factory=list)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def num_api_calls(self) -> int:
        return len(self.calls)

    @property
    def total_latency_ms(self) -> float:
        return sum(c.latency_ms for c in self.calls)

    @property
    def total_cache_read_tokens(self) -> int:
        return sum(c.cache_read_input_tokens for c in self.calls)

    @property
    def total_cache_creation_tokens(self) -> int:
        return sum(c.cache_creation_input_tokens for c in self.calls)

    def estimated_cost(self, model: str) -> float:
        """Estimated cost in dollars, accounting for prompt caching pricing.

        Cache writes: 1.25x normal input rate
        Cache reads:  0.10x normal input rate
        Regular input: 1.00x normal input rate
        """
        pricing = MODEL_PRICING.get(model) or MODEL_PRICING["claude-sonnet-4-20250514"]
        base_rate = pricing["input_per_mtok"]

        total_cost = 0.0
        for call in self.calls:
            # Regular (non-cached) input tokens
            regular_input = (
                call.input_tokens
                - call.cache_creation_input_tokens
                - call.cache_read_input_tokens
            )
            total_cost += (regular_input / 1_000_000) * base_rate
            # Cache writes at 1.25x
            total_cost += (call.cache_creation_input_tokens / 1_000_000) * base_rate * 1.25
            # Cache reads at 0.10x
            total_cost += (call.cache_read_input_tokens / 1_000_000) * base_rate * 0.1
            # Output tokens
            total_cost += (call.output_tokens / 1_000_000) * pricing["output_per_mtok"]

        return total_cost

    def format_inline(self, model: str) -> str:
        """Format for display below a chat response."""
        cost = self.estimated_cost(model)
        pricing = MODEL_PRICING.get(model) or MODEL_PRICING["claude-sonnet-4-20250514"]
        model_name = pricing["display_name"]
        cache_info = ""
        if self.total_cache_read_tokens > 0:
            cache_info = f" | {self.total_cache_read_tokens:,} cached"
        return (
            f"Stats: {model_name} | {self.num_api_calls} API call(s) | "
            f"{self.total_input_tokens:,} in + {self.total_output_tokens:,} out tokens"
            f"{cache_info} | "
            f"${cost:.4f} | {self.total_latency_ms:.0f}ms"
        )


class SessionTracker:
    """Tracks all API usage within a Streamlit session."""

    def __init__(self):
        self.responses: list = []

    @property
    def total_input_tokens(self) -> int:
        return sum(r.total_input_tokens for r in self.responses)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.total_output_tokens for r in self.responses)

    @property
    def total_cost(self) -> float:
        if not self.responses:
            return 0.0
        # Use the model from the most recent call for pricing
        last_response = self.responses[-1]
        if last_response.calls:
            model = last_response.calls[-1].model
        else:
            model = "claude-sonnet-4-20250514"
        return sum(r.estimated_cost(model) for r in self.responses)

    @property
    def total_api_calls(self) -> int:
        return sum(r.num_api_calls for r in self.responses)

    def format_sidebar(self) -> str:
        """Format summary for the Streamlit sidebar."""
        return (
            f"**Session usage**\n\n"
            f"- Questions asked: {len(self.responses)}\n"
            f"- API calls: {self.total_api_calls}\n"
            f"- Input tokens: {self.total_input_tokens:,}\n"
            f"- Output tokens: {self.total_output_tokens:,}\n"
            f"- Estimated cost: ${self.total_cost:.4f}\n"
        )
