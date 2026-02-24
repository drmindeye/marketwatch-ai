"""Telegram bot — send alert notifications using aiogram Bot API."""

import logging

from aiogram import Bot
from aiogram.enums import ParseMode

from core.config import settings

logger = logging.getLogger(__name__)

_bot: Bot | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    return _bot


def _format_alert_message(
    symbol: str,
    alert_type: str,
    price: float,
    target: float,
    ai_summary: str,
) -> str:
    type_emoji = {"touch": "🎯", "cross": "⚡", "near": "📍"}.get(alert_type, "🔔")

    return (
        f"{type_emoji} *MarketWatch Alert Triggered*\n\n"
        f"*Symbol:* `{symbol}`\n"
        f"*Type:* {alert_type.upper()}\n"
        f"*Current Price:* `{price:.5f}`\n"
        f"*Target Level:* `{target:.5f}`\n\n"
        f"🤖 *AI Summary:*\n{ai_summary}"
    )


async def send_alert(
    telegram_id: str,
    symbol: str,
    alert_type: str,
    price: float,
    target: float,
    ai_summary: str,
) -> bool:
    """Send a formatted alert message to a Telegram user."""
    bot = get_bot()
    text = _format_alert_message(symbol, alert_type, price, target, ai_summary)

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        logger.info("Telegram alert sent to %s for %s", telegram_id, symbol)
        return True
    except Exception as exc:
        logger.error("Telegram send error to %s: %s", telegram_id, exc)
        return False


async def send_text(telegram_id: str, text: str) -> bool:
    """Send a plain text Telegram message."""
    bot = get_bot()
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
        return True
    except Exception as exc:
        logger.error("Telegram text error: %s", exc)
        return False
