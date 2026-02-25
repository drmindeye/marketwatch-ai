"""Reminder worker — fires due reminders every 60 s via Telegram."""

import asyncio
import logging
from datetime import datetime, timezone

from supabase import create_client

from core.config import settings

logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # seconds

# Trading session open times in UTC (hour, minute)
SESSION_TIMES: dict[str, tuple[int, int]] = {
    "asian":    (0,  0),
    "london":   (8,  0),
    "new_york": (13, 0),
}


def _db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def _send_telegram(telegram_id: str, text: str) -> None:
    import httpx
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={"chat_id": telegram_id, "text": text, "parse_mode": "Markdown"})


async def _fire_reminder(reminder: dict, telegram_id: str | None) -> None:
    msg = f"⏰ *Reminder*\n\n{reminder['message']}"
    session = reminder.get("session_type")
    if session:
        labels = {"asian": "Asian Session 🌏", "london": "London Session 🇬🇧", "new_york": "New York Session 🇺🇸"}
        msg = f"⏰ *{labels.get(session, 'Session')} Open!*\n\n{reminder['message']}"

    if telegram_id:
        try:
            await _send_telegram(telegram_id, msg)
        except Exception as exc:
            logger.error("Reminder Telegram send failed uid=%s: %s", reminder["user_id"], exc)


async def _process_due_reminders() -> None:
    db = _db()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Fetch due, unsent reminders with profile telegram_id
    result = (
        db.table("reminders")
        .select("*, profiles(telegram_id)")
        .lte("remind_at", now_iso)
        .eq("sent", False)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return

    logger.info("Firing %d due reminder(s)", len(rows))

    for r in rows:
        profile = r.get("profiles") or {}
        telegram_id = profile.get("telegram_id")
        await _fire_reminder(r, telegram_id)

        if r.get("is_recurring") and r.get("session_type"):
            # Re-schedule for next day at the same session time
            h, m = SESSION_TIMES[r["session_type"]]
            next_dt = datetime.now(timezone.utc).replace(hour=h, minute=m, second=0, microsecond=0)
            # Advance by 1 day
            from datetime import timedelta
            next_dt = next_dt + timedelta(days=1)
            db.table("reminders").update({"remind_at": next_dt.isoformat(), "sent": False}).eq("id", r["id"]).execute()
        else:
            db.table("reminders").update({"sent": True}).eq("id", r["id"]).execute()


async def run_reminder_worker() -> None:
    logger.info("Reminder worker started (interval=%ds)", POLL_INTERVAL)
    while True:
        try:
            await _process_due_reminders()
        except Exception as exc:
            logger.error("Reminder worker error: %s", exc, exc_info=True)
        await asyncio.sleep(POLL_INTERVAL)
