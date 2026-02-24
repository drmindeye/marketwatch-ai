"""Notification dispatcher — routes triggered alerts to the right channels.

PRO / Elite → WhatsApp + Telegram
Free        → Telegram only

Each alert gets a Claude AI summary injected into the message.
"""

import asyncio
import logging
from typing import Any

from services.ai import generate_alert_summary
from services.telegram_service import send_alert as telegram_send
from services.whatsapp_service import send_alert_template as whatsapp_send

logger = logging.getLogger(__name__)


async def _notify_single(item: dict[str, Any]) -> None:
    alert = item["alert"]
    symbol: str = item["symbol"]
    price: float = item["price"]
    target: float = float(alert["price"])
    alert_type: str = alert["alert_type"]

    profile: dict[str, Any] = alert.get("profiles") or {}
    tier: str = profile.get("tier", "free")
    telegram_id: str | None = profile.get("telegram_id")
    whatsapp: str | None = profile.get("whatsapp")

    # Generate AI summary (runs in thread to avoid blocking event loop)
    try:
        ai_summary = await asyncio.to_thread(
            generate_alert_summary, symbol, price, alert_type, target
        )
    except Exception as exc:
        logger.warning("AI summary failed for %s: %s — using fallback", symbol, exc)
        ai_summary = f"{symbol} hit your {alert_type} level at {price:.5f}."

    tasks: list[asyncio.coroutine] = []

    # Telegram — all tiers
    if telegram_id:
        tasks.append(
            telegram_send(
                telegram_id=telegram_id,
                symbol=symbol,
                alert_type=alert_type,
                price=price,
                target=target,
                ai_summary=ai_summary,
            )
        )
    else:
        logger.warning("No telegram_id for user — skipping Telegram alert")

    # WhatsApp — PRO and Elite only
    if tier in ("pro", "elite") and whatsapp:
        tasks.append(
            whatsapp_send(
                phone=whatsapp,
                symbol=symbol,
                alert_type=alert_type,
                price=price,
                target=target,
                ai_summary=ai_summary,
            )
        )

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error("Notification dispatch error: %s", r)

    logger.info(
        "Dispatched [%s] %s @ %.5f → tier=%s telegram=%s whatsapp=%s",
        alert_type,
        symbol,
        price,
        tier,
        bool(telegram_id),
        bool(tier in ("pro", "elite") and whatsapp),
    )


async def dispatch_notifications(notifications: list[dict[str, Any]]) -> None:
    """Dispatch all triggered alerts concurrently."""
    if not notifications:
        return
    await asyncio.gather(*[_notify_single(n) for n in notifications])
