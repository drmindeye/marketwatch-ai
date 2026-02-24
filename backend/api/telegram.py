"""Telegram webhook — alerts + AI chat via Claude."""

import asyncio
import logging
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Request
from supabase import create_client

from core.config import settings
from services.ai import chat as claude_chat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/telegram", tags=["telegram"])

_dp = Dispatcher()
_bot: Bot | None = None

# In-memory per-user chat history (telegram_id → list of messages)
# Resets on redeploy — good enough for session context
_chat_history: dict[str, list[dict[str, str]]] = {}

FREE_LIMIT = 3  # free users get 3 AI messages per session


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    return _bot


async def _get_user_tier(telegram_id: str) -> str:
    """Look up the user's tier from Supabase by their telegram_id."""
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        result = (
            supabase.table("profiles")
            .select("tier")
            .eq("telegram_id", str(telegram_id))
            .single()
            .execute()
        )
        return result.data["tier"] if result.data else "free"
    except Exception:
        return "free"


async def _link_account(bot: Bot, chat_id: int, email: str) -> None:
    """Link this Telegram ID to a MarketWatch account by email."""
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        result = (
            supabase.table("profiles")
            .update({"telegram_id": str(chat_id)})
            .eq("email", email.lower().strip())
            .execute()
        )
        if result.data:
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ *Account linked\\!*\n\n"
                    f"Your Telegram is now connected to *{email}*\\.\n"
                    f"You'll receive price alerts here from now on\\."
                ),
                parse_mode="MarkdownV2",
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ No account found with that email. Make sure you're registered at MarketWatch AI.",
            )
    except Exception as exc:
        logger.error("Link account error: %s", exc)
        await bot.send_message(chat_id=chat_id, text="⚠️ Something went wrong. Please try again.")


async def _handle_message(bot: Bot, chat_id: int, text: str) -> None:
    """Route incoming message to the right handler."""
    tid = str(chat_id)
    text = text.strip()

    # /start — welcome + show Telegram ID
    if text == "/start":
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"👋 *Welcome to MarketWatch AI\\!*\n\n"
                f"Your Telegram ID is:\n`{chat_id}`\n\n"
                f"To receive price alerts, link your account:\n"
                f"`/link your@email\\.com`\n\n"
                f"💬 You can also ask me any market question and I'll answer using AI\\.\n"
                f"Free users get {FREE_LIMIT} questions per session\\. "
                f"Upgrade to *PRO* for unlimited AI chat\\."
            ),
            parse_mode="MarkdownV2",
        )
        return

    # /link <email>
    if text.startswith("/link"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or "@" not in parts[1]:
            await bot.send_message(
                chat_id=chat_id,
                text="Usage: /link your@email.com",
            )
            return
        await _link_account(bot, chat_id, parts[1])
        return

    # /help
    if text == "/help":
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🤖 *MarketWatch AI Bot*\n\n"
                "/start \\- Welcome message\n"
                "/link email \\- Link your MarketWatch account\n"
                "/clear \\- Clear chat history\n"
                "/help \\- Show this message\n\n"
                "Or just type any market question\\!"
            ),
            parse_mode="MarkdownV2",
        )
        return

    # /clear — reset chat history
    if text == "/clear":
        _chat_history.pop(tid, None)
        await bot.send_message(chat_id=chat_id, text="🗑 Chat history cleared.")
        return

    # AI chat — check tier
    tier = await _get_user_tier(tid)

    history = _chat_history.get(tid, [])

    # Free tier limit
    user_messages = [m for m in history if m["role"] == "user"]
    if tier == "free" and len(user_messages) >= FREE_LIMIT:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"⚠️ You've used your {FREE_LIMIT} free AI questions this session.\n\n"
                "Upgrade to *PRO* at marketwatch-ai for unlimited AI chat!"
            ),
            parse_mode="Markdown",
        )
        return

    # Add user message to history
    history.append({"role": "user", "content": text})
    _chat_history[tid] = history

    # Show typing indicator
    await bot.send_chat_action(chat_id=chat_id, action="typing")

    # Call Claude in thread (blocking SDK)
    try:
        reply = await asyncio.to_thread(claude_chat, history)
    except Exception as exc:
        logger.error("Claude chat error for %s: %s — %r", tid, type(exc).__name__, str(exc))
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ AI is temporarily unavailable. Please try again shortly.",
        )
        return

    # Add assistant reply to history (keep last 20 messages to avoid token bloat)
    history.append({"role": "assistant", "content": reply})
    _chat_history[tid] = history[-20:]

    await bot.send_message(chat_id=chat_id, text=reply)


@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict[str, Any]:
    """Receive updates from Telegram and dispatch."""
    body = await request.json()
    bot = get_bot()

    update = Update.model_validate(body)

    if update.message and update.message.text:
        chat_id = update.message.chat.id
        text = update.message.text
        logger.info("Telegram message from %s: %s", chat_id, text[:50])
        await _handle_message(bot, chat_id, text)

    await _dp.feed_update(bot=bot, update=update)
    return {"ok": True}
