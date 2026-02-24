"""Background worker — polls FMP every 30 s and fires alert checks."""

import asyncio
import logging

from supabase import create_client

from core.config import settings
from services.fmp import fetch_batch_quotes
from services.alert_engine import check_alerts

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds


async def _get_active_symbols() -> list[str]:
    """Return all unique symbols that have active, untriggered alerts."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    result = (
        supabase.table("alerts")
        .select("symbol")
        .eq("is_active", True)
        .is_("triggered_at", "null")
        .execute()
    )
    if not result.data:
        return []
    return list({row["symbol"] for row in result.data})


async def run_worker() -> None:
    """Main polling loop — runs for the lifetime of the FastAPI process."""
    logger.info("FMP worker started (interval=%ds)", POLL_INTERVAL)

    while True:
        try:
            symbols = await _get_active_symbols()

            if symbols:
                quotes = await fetch_batch_quotes(symbols)
                if quotes:
                    await check_alerts(quotes)
            else:
                logger.debug("No active alert symbols — skipping FMP call")

        except Exception as exc:
            logger.error("Worker loop error: %s", exc, exc_info=True)

        await asyncio.sleep(POLL_INTERVAL)
