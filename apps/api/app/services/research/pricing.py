"""Per-model USD pricing for research-agent cost estimation.

Prices are $ per 1M tokens (input, output). Used to estimate the cost of a
completed research run so we can enforce a daily USD budget on Anthropic
usage and show the user what each run actually cost. Update this table if
pricing changes or a new model is introduced.
"""

from __future__ import annotations

# (input $/1M tokens, output $/1M tokens)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
    # Groq (fallback provider — effectively free at this project's scale)
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
}

# Fallback for an unlisted model: assume Haiku-tier pricing rather than $0, so
# an unrecognized model can't silently defeat the budget check.
_DEFAULT_PRICING = MODEL_PRICING["claude-haiku-4-5"]


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    input_price, output_price = MODEL_PRICING.get(model, _DEFAULT_PRICING)
    return (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
