"""Alert trigger logic: Touch, Cross, Near, Zone."""

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import create_client

from core.config import settings

logger = logging.getLogger(__name__)


def _pip_size(symbol: str) -> float:
    if "JPY" in symbol:
        return 0.01
    if any(c in symbol for c in ("BTC", "ETH", "XRP", "GOLD", "XAU")):
        return 0.01
    return 0.0001


def _is_triggered(
    alert: dict[str, Any],
    price: float,
    prev_price: float | None = None,
) -> bool:
    """Return True if the current (or crossed) price satisfies the alert condition."""
    target: float = float(alert["price"])
    direction: str | None = alert.get("direction")
    alert_type: str = alert["alert_type"]
    pip_buf: float = float(alert.get("pip_buffer") or 5)
    pip: float = _pip_size(alert["symbol"])
    buffer: float = pip_buf * pip

    match alert_type:
        case "touch":
            if direction == "above":
                # Fires when price reaches or crosses target from below
                hit = price >= target
                # Also catch if price jumped over target between polls
                crossed = (
                    prev_price is not None
                    and prev_price < target
                    and price > target
                )
                return hit or crossed

            if direction == "below":
                hit = price <= target
                crossed = (
                    prev_price is not None
                    and prev_price > target
                    and price < target
                )
                return hit or crossed

            # No direction — fire when price is within buffer OR crossed the target
            within = abs(price - target) <= buffer
            crossed = prev_price is not None and (
                (prev_price < target <= price) or
                (prev_price > target >= price)
            )
            return within or crossed

        case "cross":
            if direction == "above":
                # Strict cross: previous price must have been below
                if prev_price is not None:
                    return prev_price < target <= price
                return price >= target
            if direction == "below":
                if prev_price is not None:
                    return prev_price > target >= price
                return price <= target
            return False

        case "near":
            return abs(price - target) <= buffer

        case "zone":
            zone_high = alert.get("zone_high")
            if zone_high is None:
                return False
            low, high = float(target), float(zone_high)
            # Current price inside zone
            if low <= price <= high:
                return True
            # Price crossed into zone between polls
            if prev_price is not None:
                return (prev_price < low <= price) or (prev_price > high >= price)
            return False

    return False


async def check_alerts(
    quotes: dict[str, dict[str, Any]],
    prev_quotes: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Evaluate all active alerts against the latest quotes, fire triggers."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    symbols = list(quotes.keys())
    result = (
        supabase.table("alerts")
        .select("*, profiles(tier, whatsapp, telegram_id, email)")
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

        # Previous price for crossing detection
        prev_price: float | None = None
        if prev_quotes and symbol in prev_quotes:
            prev_price = float(prev_quotes[symbol].get("price", 0)) or None

        if _is_triggered(alert, price, prev_price):
            triggered_ids.append(alert["id"])
            notifications.append({
                "alert": alert,
                "price": price,
                "symbol": symbol,
            })
            logger.info(
                "TRIGGERED: %s %s @ %.5f (target=%.5f prev=%s type=%s)",
                alert["alert_type"],
                symbol,
                price,
                float(alert["price"]),
                f"{prev_price:.5f}" if prev_price else "n/a",
                alert["alert_type"],
            )

    if not triggered_ids:
        return

    now = datetime.now(timezone.utc).isoformat()
    supabase.table("alerts").update(
        {"triggered_at": now, "is_active": False}
    ).in_("id", triggered_ids).execute()

    from services.notifier import dispatch_notifications
    await dispatch_notifications(notifications)


async def check_correlation_alerts(
    quotes: dict[str, dict[str, Any]],
    prev_quotes: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Check active correlation zone alerts — fires when either pair enters the zone."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    result = (
        supabase.table("correlation_alerts")
        .select("*, profiles(tier, telegram_id, whatsapp, email)")
        .eq("is_active", True)
        .is_("triggered_at", "null")
        .execute()
    )
    if not result.data:
        return

    triggered_ids: list[str] = []
    updates: list[tuple[str, str]] = []  # (id, triggered_by)
    notifications: list[dict[str, Any]] = []

    for alert in result.data:
        sym1: str = alert["symbol1"]
        sym2: str = alert["symbol2"]
        zone_low: float = float(alert["zone_low"])
        zone_high: float = float(alert["zone_high"])

        triggered_by: str | None = None
        triggered_price: float | None = None

        for sym in (sym1, sym2):
            q = quotes.get(sym)
            if not q:
                continue
            price = float(q.get("price", 0))
            if price <= 0:
                continue
            prev_price: float | None = None
            if prev_quotes and sym in prev_quotes:
                prev_price = float(prev_quotes[sym].get("price", 0)) or None

            in_zone = zone_low <= price <= zone_high
            crossed = prev_price is not None and (
                (prev_price < zone_low <= price) or
                (prev_price > zone_high >= price)
            )
            if in_zone or crossed:
                triggered_by = sym
                triggered_price = price
                break

        if triggered_by and triggered_price is not None:
            triggered_ids.append(alert["id"])
            updates.append((alert["id"], triggered_by))
            notifications.append({
                "alert": alert,
                "symbol": triggered_by,
                "price": triggered_price,
            })
            logger.info(
                "CORRELATION TRIGGERED: %s/%s zone [%.5f-%.5f] — %s @ %.5f",
                sym1, sym2, zone_low, zone_high, triggered_by, triggered_price,
            )

    if not triggered_ids:
        return

    now = datetime.now(timezone.utc).isoformat()
    for alert_id, trig_sym in updates:
        supabase.table("correlation_alerts").update(
            {"triggered_at": now, "is_active": False, "triggered_by": trig_sym}
        ).eq("id", alert_id).execute()

    from services.notifier import dispatch_correlation_notifications
    await dispatch_correlation_notifications(notifications)
