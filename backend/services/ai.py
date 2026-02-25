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


REMINDER_PARSE_PROMPT = """You are a reminder parser for a trading bot. The user wants to set a reminder.
Extract the reminder details and return ONLY valid JSON with these fields:
- "message": string — what to remind them about (concise, 1-2 sentences)
- "remind_at": string — ISO 8601 UTC datetime for when to fire the reminder
- "session_type": string or null — one of "asian", "london", "new_york" if it's a session reminder, else null
- "is_recurring": boolean — true if they want it daily (sessions are always recurring)

Current UTC time: {now_utc}

Session open times (UTC):
- Asian session: 00:00 UTC
- London session: 08:00 UTC
- New York session: 13:00 UTC

Rules:
- If asking about a trading session, set session_type and is_recurring=true, remind_at = next occurrence
- If a specific time is given (e.g. "2am"), convert to UTC and set remind_at accordingly
- For "tomorrow", advance date by 1 day
- Always return valid JSON only — no explanation, no markdown fences"""


def parse_reminder(user_text: str, now_utc: str) -> dict | None:
    """Parse a natural-language reminder request into structured data."""
    import json
    prompt = REMINDER_PARSE_PROMPT.format(now_utc=now_utc)
    try:
        response = _get_client().chat.completions.create(
            model=MODEL,
            max_tokens=200,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        # Strip markdown fences if model includes them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        return None
