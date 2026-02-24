"""Alert trigger logic: Touch, Cross, Near Level."""

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import create_client

from core.config import settings

logger = logging.getLogger(__name__)

# 1 pip = 0.0001 for 4-decimal pairs (EURUSD), 0.01 for JPY pairs, 0.01 for crypto
# We store pip_buffer as number of pips; convert to price units here.
DEFAULT_PIP_SIZE = 0.0001


def _pip_size(symbol: str) -> float:
    """Return pip size in price units for a given symbol."""
    if "JPY" in symbol:
        return 0.01
    if any(c in symbol for c in ("BTC", "ETH", "XRP", "GOLD", "XAU")):
        return 0.01
    return 0.0001


def _is_triggered(alert: dict[str, Any], price: float) -> bool:
    """Return True if the current price satisfies the alert condition."""
    target: float = float(alert["price"])
    direction: str | None = alert.get("direction")
    alert_type: str = alert["alert_type"]
    pip_buf: float = float(alert.get("pip_buffer") or 5)
    pip: float = _pip_size(alert["symbol"])
    buffer: float = pip_buf * pip

    match alert_type:
        case "touch":
            # Price has reached or passed the target level
            if direction == "above":
                return price >= target
            if direction == "below":
                return price <= target
            return abs(price - target) < buffer

        case "cross":
            # We need previous price to detect a cross — stored in metadata
            # For now treat like touch; cross detection enhanced in run loop
            if direction == "above":
                return price >= target
            if direction == "below":
                return price <= target
            return False

        case "near":
            return abs(price - target) <= buffer

    return False


async def check_alerts(quotes: dict[str, dict[str, Any]]) -> None:
    """Evaluate all active alerts against the latest quotes, fire triggers."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    # Fetch all active alerts for symbols we have quotes for
    symbols = list(quotes.keys())
    result = (
        supabase.table("alerts")
        .select("*, profiles(tier, whatsapp, telegram_id)")
        .eq("is_active", True)
        .is_("triggered_at", "null")
        .in_("symbol", symbols)
        .execute()
    )

    if not result.data:
        return

    triggered_ids: list[str] = []
    notifications: list[dict[str, Any]] = []

    for alert in result.data:
        symbol = alert["symbol"]
        quote = quotes.get(symbol)
        if not quote:
            continue

        price: float = float(quote.get("price", 0))
        if price <= 0:
            continue

        if _is_triggered(alert, price):
            triggered_ids.append(alert["id"])
            notifications.append(
                {
                    "alert": alert,
                    "price": price,
                    "symbol": symbol,
                }
            )
            logger.info(
                "Alert triggered: %s %s @ %.5f (target %.5f, type=%s)",
                alert["alert_type"],
                symbol,
                price,
                float(alert["price"]),
                alert["alert_type"],
            )

    if not triggered_ids:
        return

    # Mark alerts as triggered
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("alerts").update(
        {"triggered_at": now, "is_active": False}
    ).in_("id", triggered_ids).execute()

    # Dispatch notifications (import here to avoid circular)
    from services.notifier import dispatch_notifications
    await dispatch_notifications(notifications)
