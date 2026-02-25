"""Profile management — link Telegram/WhatsApp from dashboard."""

import logging

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from supabase import create_client

from api.alerts import _get_user_id
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/profile", tags=["profile"])


def _db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


class LinkBody(BaseModel):
    telegram_id: str | None = None
    whatsapp: str | None = None


async def _send_telegram_message(chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=8) as client:
        await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})


@router.post("/link")
async def link_channels(body: LinkBody, authorization: str = Header(...)) -> dict:
    """Save Telegram ID and/or WhatsApp number from the dashboard settings page.

    If a telegram_id is provided and the bot token is configured, sends a
    welcome confirmation directly to the user's Telegram chat.
    """
    user_id = _get_user_id(authorization)
    db = _db()

    update: dict = {}
    if body.telegram_id is not None:
        update["telegram_id"] = body.telegram_id or None
    if body.whatsapp is not None:
        update["whatsapp"] = body.whatsapp or None

    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")

    result = db.table("profiles").update(update).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Send Telegram confirmation if a telegram_id was linked
    if body.telegram_id:
        try:
            profile = db.table("profiles").select("email, tier").eq("id", user_id).single().execute()
            email = (profile.data or {}).get("email", "")
            tier = (profile.data or {}).get("tier", "free").upper()
            msg = (
                f"✅ *MarketWatch AI — Account Linked!*\n\n"
                f"Your Telegram is now connected to `{email}`.\n"
                f"Plan: *{tier}*\n\n"
                f"Use /menu to get started. Happy trading! 🚀"
            )
            await _send_telegram_message(body.telegram_id, msg)
        except Exception as exc:
            logger.warning("Could not send Telegram link confirmation: %s", exc)

    return {"ok": True}
