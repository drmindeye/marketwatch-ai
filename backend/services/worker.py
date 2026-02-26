"""Background worker — polls FMP every 30 s and fires alert checks."""

import asyncio
import logging
from typing import Any

from supabase import create_client

from core.config import settings
from services.fmp import fetch_batch_quotes
from services.alert_engine import check_alerts, check_correlation_alerts

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds


async def _get_active_symbols() -> list[str]:
    """Return all unique symbols needed by active regular AND correlation alerts."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    symbols: set[str] = set()

    # Regular alerts
    r = (
        supabase.table("alerts")
        .select("symbol")
        .eq("is_active", True)
        .is_("triggered_at", "null")
        .execute()
    )
    for row in (r.data or []):
        symbols.add(row["symbol"])

    # Correlation alerts — need both symbol1 and symbol2
    rc = (
        supabase.table("correlation_alerts")
        .select("symbol1,symbol2")
        .eq("is_active", True)
        .is_("triggered_at", "null")
        .execute()
    )
    for row in (rc.data or []):
        symbols.add(row["symbol1"])
        symbols.add(row["symbol2"])

    return list(symbols)


async def run_worker() -> None:
    """Main polling loop — runs for the lifetime of the FastAPI process."""
    logger.info("FMP worker started (interval=%ds)", POLL_INTERVAL)

    prev_quotes: dict[str, dict[str, Any]] = {}

    while True:
        try:
            symbols = await _get_active_symbols()

            if symbols:
                quotes = await fetch_batch_quotes(symbols)
                if quotes:
                    await check_alerts(quotes, prev_quotes)
                    await check_correlation_alerts(quotes, prev_quotes)
                    prev_quotes = {s: quotes[s] for s in quotes}
            else:
                logger.debug("No active alert symbols — skipping FMP call")
                prev_quotes.clear()

        except Exception as exc:
            logger.error("Worker loop error: %s", exc, exc_info=True)

        await asyncio.sleep(POLL_INTERVAL)
