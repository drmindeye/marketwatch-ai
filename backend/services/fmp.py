import logging
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

# Use the v3 batch endpoint: /api/v3/quote/SYM1,SYM2,SYM3
# The stable endpoint only accepts a single symbol; v3 accepts comma-separated
# symbols in the URL path — one API call regardless of how many symbols.
FMP_V3 = "https://financialmodelingprep.com/api/v3"


async def fetch_batch_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch quotes for all symbols in a single FMP v3 batch call."""
    if not symbols:
        return {}

    joined = ",".join(symbols)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{FMP_V3}/quote/{joined}",
                params={"apikey": settings.FMP_API_KEY},
            )
            resp.raise_for_status()
            data: list[dict[str, Any]] = resp.json()
            if not data or not isinstance(data, list):
                logger.warning("FMP v3 batch returned empty for: %s", joined)
                return {}
            result = {item["symbol"]: item for item in data if item.get("symbol")}
            logger.debug("FMP v3 batch: got %d/%d symbols", len(result), len(symbols))
            return result
    except httpx.HTTPStatusError as exc:
        logger.error("FMP v3 HTTP %s for [%s]", exc.response.status_code, joined)
    except Exception as exc:
        logger.error("FMP v3 batch error for [%s]: %s", joined, exc)
    return {}
