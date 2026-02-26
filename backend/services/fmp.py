import logging
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/stable"


async def fetch_batch_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch quotes for all symbols in a single FMP API call.

    Uses comma-separated symbols in one request instead of N individual calls,
    keeping API usage at 1 call per poll cycle regardless of how many symbols
    are being watched.
    """
    if not symbols:
        return {}

    joined = ",".join(symbols)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{FMP_BASE}/quote",
                params={"symbol": joined, "apikey": settings.FMP_API_KEY},
            )
            resp.raise_for_status()
            data: list[dict[str, Any]] = resp.json()
            if not data or not isinstance(data, list):
                logger.warning("FMP batch returned empty for symbols: %s", joined)
                return {}
            result = {item["symbol"]: item for item in data if item.get("symbol")}
            logger.debug("FMP batch fetched %d/%d symbols", len(result), len(symbols))
            return result
    except httpx.HTTPStatusError as exc:
        logger.error("FMP batch HTTP %s for [%s]", exc.response.status_code, joined)
    except Exception as exc:
        logger.error("FMP batch quote error for [%s]: %s", joined, exc)
    return {}
