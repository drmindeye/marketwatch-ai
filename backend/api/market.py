"""Public market data endpoint — live prices for a list of symbols."""

from fastapi import APIRouter, HTTPException, Query

from services.fmp import fetch_batch_quotes

router = APIRouter(prefix="/api/market", tags=["market"])

MAX_SYMBOLS = 20


@router.get("/prices")
async def get_prices(symbols: str = Query(..., description="Comma-separated symbols")) -> dict:
    """Return live price + daily change% for up to 20 symbols."""
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="symbols parameter is required")
    if len(symbol_list) > MAX_SYMBOLS:
        raise HTTPException(status_code=400, detail=f"Max {MAX_SYMBOLS} symbols per request")

    quotes = await fetch_batch_quotes(symbol_list)

    return {
        symbol: {
            "price": q.get("price"),
            "change": round(q.get("changesPercentage") or 0, 3),
            "name": q.get("name", symbol),
        }
        for symbol, q in quotes.items()
    }
