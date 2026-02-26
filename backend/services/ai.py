"""DeepSeek AI — market summaries, multi-timeframe analysis, reminders, chat."""

import re
from openai import OpenAI

from core.config import settings

MODEL = "deepseek-chat"

# ── System prompts ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are MarketWatch AI — a professional trading assistant for Forex and crypto traders.

RULES:
- Never give financial advice. Provide analysis only.
- Be direct, structured, and concise.
- When you have a live price injected in context, ALL zones must be within realistic distance of that price.
- Do NOT invent price levels from your training data if a live price is provided — anchor everything to it.

MULTI-TIMEFRAME ANALYSIS FORMAT (use this whenever a user asks for analysis on a pair or asset):
When a LIVE PRICE is provided, give zones for each timeframe that make sense relative to that exact price.
Structure your reply exactly like this (adjust decimals to match the instrument):

📊 {SYMBOL} — Live: {PRICE}
━━━━━━━━━━━━━━━━━━━━━━━
⏱ 15M │ Bias: {Bull/Bear/Neutral} │ Res: {level} │ Sup: {level}
⏱ 1H  │ Bias: {Bull/Bear/Neutral} │ Res: {level} │ Sup: {level}
⏱ 4H  │ Bias: {Bull/Bear/Neutral} │ Res: {level} │ Sup: {level}
⏱ D   │ Bias: {Bull/Bear/Neutral} │ Res: {level} │ Sup: {level}
⏱ M   │ Bias: {Bull/Bear/Neutral} │ Res: {level} │ Sup: {level}
━━━━━━━━━━━━━━━━━━━━━━━
📝 {1-2 sentence context — what is driving price right now}
🎯 Watch: {the single most important level to watch right now}

ZONE DISTANCE RULES (zones must be realistic — not from a different era):
- 15M zones: within 0.05% of live price
- 1H zones: within 0.15% of live price
- 4H zones: within 0.4% of live price
- Daily zones: within 1% of live price
- Monthly zones: within 3% of live price

For crypto (BTC, ETH): use whole numbers or 1 decimal. For Forex majors: 5 decimal places. For JPY pairs: 3 decimals. For Gold: 2 decimals."""

ALERT_SYSTEM_PROMPT = """You are MarketWatch AI's alert analyst. Give a 2-3 sentence market context
when a price alert fires. Be direct. Never give financial advice."""


# ── Symbol detection ───────────────────────────────────────────────────────────

# Common aliases → FMP symbol
_ALIASES: dict[str, str] = {
    "gold": "XAUUSD",
    "xau": "XAUUSD",
    "bitcoin": "BTCUSD",
    "btc": "BTCUSD",
    "ethereum": "ETHUSD",
    "eth": "ETHUSD",
    "ether": "ETHUSD",
    "dollar index": "DXY",
    "dxy": "DXY",
    "oil": "USOIL",
    "crude": "USOIL",
    "silver": "XAGUSD",
    "xag": "XAGUSD",
}

_SYMBOL_RE = re.compile(
    r"\b([A-Z]{3}[\/\-]?[A-Z]{3})\b",
    re.IGNORECASE,
)


def detect_symbol(text: str) -> str | None:
    """Extract the first trading symbol from user text."""
    lower = text.lower()
    for alias, sym in _ALIASES.items():
        if alias in lower:
            return sym

    match = _SYMBOL_RE.search(text)
    if match:
        return match.group(1).replace("/", "").replace("-", "").upper()

    return None


# ── Client ────────────────────────────────────────────────────────────────────

def _get_client() -> OpenAI:
    return OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )


# ── Core chat ─────────────────────────────────────────────────────────────────

def chat(messages: list[dict[str, str]], price_context: str | None = None) -> str:
    """Multi-turn AI chat. Optionally inject live price context."""
    system = SYSTEM_PROMPT
    if price_context:
        system = SYSTEM_PROMPT + f"\n\nLIVE MARKET DATA (use this — do not use training data prices):\n{price_context}"

    response = _get_client().chat.completions.create(
        model=MODEL,
        max_tokens=700,
        messages=[{"role": "system", "content": system}] + messages,
    )
    return response.choices[0].message.content or ""


# ── Alert summary ─────────────────────────────────────────────────────────────

def generate_alert_summary(symbol: str, price: float, alert_type: str, target: float) -> str:
    """Generate a brief AI market summary when an alert fires."""
    prompt = (
        f"Alert fired: {symbol} is NOW at {price:.5f} "
        f"(alert type: {alert_type}, target level: {target:.5f}). "
        f"Give a 2-3 sentence market context. Current price is {price:.5f} — base your analysis on this exact level."
    )
    response = _get_client().chat.completions.create(
        model=MODEL,
        max_tokens=180,
        messages=[
            {"role": "system", "content": ALERT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""


# ── Reminder parser ───────────────────────────────────────────────────────────

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
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        return None
