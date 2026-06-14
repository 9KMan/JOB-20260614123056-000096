"""Per-model cost estimation. USD per 1k tokens (input / output)."""

from __future__ import annotations

from typing import Tuple


# Source: provider pricing pages. Update as needed.
# IMPORTANT: more-specific keys MUST come before less-specific keys so
# that "gpt-4o-mini" doesn't get matched as "gpt-4o".
MODEL_PRICING: dict[str, Tuple[float, float]] = {
    # (input_usd_per_1k, output_usd_per_1k)
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-4o": (0.0025, 0.01),
    "claude-3-5-haiku": (0.0008, 0.004),
    "claude-3-5-sonnet": (0.003, 0.015),
    "claude-3-opus": (0.015, 0.075),
}


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    """Return estimated cost in USD for the given token counts."""
    # Match by prefix (e.g. "gpt-4o-2024-08-06" -> "gpt-4o")
    for key, (pin, pout) in MODEL_PRICING.items():
        if model.startswith(key):
            return (tokens_in / 1000.0) * pin + (tokens_out / 1000.0) * pout
    # Unknown model: best-effort using gpt-4o-mini pricing
    pin, pout = MODEL_PRICING["gpt-4o-mini"]
    return (tokens_in / 1000.0) * pin + (tokens_out / 1000.0) * pout


def estimate_cost_cents(model: str, tokens_in: int, tokens_out: int) -> float:
    """Return estimated cost in cents."""
    return estimate_cost_usd(model, tokens_in, tokens_out) * 100.0
