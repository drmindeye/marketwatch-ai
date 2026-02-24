import asyncio
import logging
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/stable"
MAX_CONCURRENT = 10  # Stay well under 300 calls/min


async def _fetch_single(client: httpx.AsyncClient, symbol: str) -> tuple[str, dict[str, Any] | None]:
    """Fetch a single symbol quote from FMP stable API."""
    try:
        resp = await client.get(
            f"{FMP_BASE}/quote",
            params={"symbol": symbol, "apikey": settings.FMP_API_KEY},
        )
        resp.raise_for_status()
        data: list[dict[str, Any]] = resp.json()
        if data and isinstance(data, list):
            return symbol, data[0]
    except Exception as exc:
        logger.error("FMP quote error for %s: %s", symbol, exc)
    return symbol, None


async def fetch_batch_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch quotes for multiple symbols concurrently.

    Uses semaphore to cap concurrency at MAX_CONCURRENT requests at a time,
    keeping us well under FMP's 300 calls/min limit.
    """
    if not symbols:
        return {}

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def guarded_fetch(client: httpx.AsyncClient, symbol: str):
        async with semaphore:
            return await _fetch_single(client, symbol)

    async with httpx.AsyncClient(timeout=10) as client:
        results = await asyncio.gather(
            *[guarded_fetch(client, s) for s in symbols]
        )

    return {symbol: data for symbol, data in results if data is not None}
