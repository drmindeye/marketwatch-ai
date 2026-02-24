"""DeepSeek AI — market summaries and chat via OpenAI-compatible SDK."""

from openai import OpenAI

from core.config import settings

MODEL = "deepseek-chat"

SYSTEM_PROMPT = """You are MarketWatch AI's trading assistant. You provide concise,
actionable Forex and market insights. Keep summaries under 120 words.
Never give financial advice — only analysis. Be direct and professional."""


def _get_client() -> OpenAI:
    return OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )


def generate_alert_summary(symbol: str, price: float, alert_type: str, target: float) -> str:
    """Generate a brief AI market summary when an alert fires."""
    prompt = (
        f"An alert just triggered: {symbol} is at {price:.5f} "
        f"(alert type: {alert_type}, target level: {target:.5f}). "
        f"Give a 2-3 sentence market context for {symbol} right now."
    )

    response = _get_client().chat.completions.create(
        model=MODEL,
        max_tokens=180,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content or ""


def chat(messages: list[dict[str, str]]) -> str:
    """Multi-turn AI chat."""
    response = _get_client().chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
    )

    return response.choices[0].message.content or ""
