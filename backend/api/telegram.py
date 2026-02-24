"""Telegram webhook — receive bot updates from Telegram."""

import logging
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Request

from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/telegram", tags=["telegram"])

_dp = Dispatcher()
_bot: Bot | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    return _bot


@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict[str, Any]:
    """Receive updates from Telegram and dispatch through aiogram."""
    body = await request.json()

    bot = get_bot()
    update = Update.model_validate(body)

    # Log the chat ID so users can share it for alert registration
    if update.message and update.message.text == "/start":
        chat_id = update.message.chat.id
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"👋 Welcome to MarketWatch AI!\n\n"
                f"Your Telegram ID is: `{chat_id}`\n\n"
                f"Add this in your MarketWatch profile to receive alerts here."
            ),
            parse_mode="Markdown",
        )
        logger.info("New Telegram /start from chat_id=%s", chat_id)

    await _dp.feed_update(bot=bot, update=update)
    return {"ok": True}
