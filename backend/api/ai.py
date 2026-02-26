import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.ai import chat, detect_symbol
from services.fmp import fetch_batch_quotes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["ai"])


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    user_tier: str = "free"


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(req: ChatRequest) -> ChatResponse:
    if req.user_tier not in ("pro", "elite"):
        raise HTTPException(status_code=403, detail="AI chat requires Pro or Elite plan")

    if not req.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    # Detect symbol in the latest user message and inject live price context
    price_context: str | None = None
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    symbol = detect_symbol(last_user)
    if symbol:
        try:
            quotes = await fetch_batch_quotes([symbol])
            q = quotes.get(symbol)
            if q:
                price = q.get("price", 0)
                chg = q.get("changesPercentage", 0)
                price_context = (
                    f"{symbol} live price: {price} ({chg:+.2f}% today)\n"
                    f"Base ALL zones and levels on this exact current price."
                )
        except Exception as exc:
            logger.warning("Price fetch for AI context failed (%s): %s", symbol, exc)

    reply = chat(messages, price_context)
    return ChatResponse(reply=reply)
