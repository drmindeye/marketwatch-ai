import logging
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/api/v3"


async def fetch_batch_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch quotes for multiple symbols in a single FMP API call.

    Returns a dict keyed by symbol e.g. {"EURUSD": {"price": 1.085, ...}}
    Batching keeps us well under the 300 calls/min limit.
    """
    if not symbols:
        return {}

    joined = ",".join(symbols)
    url = f"{FMP_BASE}/quote/{joined}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params={"apikey": settings.FMP_API_KEY})
            resp.raise_for_status()
            data: list[dict[str, Any]] = resp.json()
    except Exception as exc:
        logger.error("FMP batch quote error: %s", exc)
        return {}

    return {item["symbol"]: item for item in data if "symbol" in item}
