from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.ai import chat

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
    reply = chat(messages)
    return ChatResponse(reply=reply)
