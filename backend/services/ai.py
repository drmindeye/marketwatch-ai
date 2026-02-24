"""Claude 3.5 Sonnet — market summaries and AI chat."""

import anthropic

from core.config import settings

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are MarketWatch AI's trading assistant. You provide concise,
actionable Forex and market insights. Keep summaries under 120 words.
Never give financial advice — only analysis. Be direct and professional."""


def _get_client() -> anthropic.Anthropic:
    """Lazy-load the Anthropic client so it always uses the current env var."""
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def generate_alert_summary(symbol: str, price: float, alert_type: str, target: float) -> str:
    """Generate a brief AI market summary when an alert fires."""
    prompt = (
        f"An alert just triggered: {symbol} is at {price:.5f} "
        f"(alert type: {alert_type}, target level: {target:.5f}). "
        f"Give a 2-3 sentence market context for {symbol} right now."
    )

    message = _get_client().messages.create(
        model=MODEL,
        max_tokens=180,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text  # type: ignore[index]


def chat(messages: list[dict[str, str]]) -> str:
    """Multi-turn AI chat."""
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text  # type: ignore[index]
