"""WhatsApp Cloud API webhook — verify challenge and receive messages."""

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from core.config import settings
from services.whatsapp_service import verify_whatsapp_signature

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


@router.get("/webhook", response_class=PlainTextResponse)
async def whatsapp_verify(
    hub_mode: str = "",
    hub_verify_token: str = "",
    hub_challenge: str = "",
) -> str:
    """Meta webhook verification handshake."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified")
        return hub_challenge
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook", status_code=200)
async def whatsapp_receive(
    request: Request,
    x_hub_signature_256: str = Header(default=""),
) -> dict:
    """Receive incoming WhatsApp messages — signature verified before processing."""
    payload = await request.body()

    if x_hub_signature_256 and not verify_whatsapp_signature(payload, x_hub_signature_256):
        logger.warning("WhatsApp webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON")

    # Extract incoming messages if present
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                from_number = msg.get("from", "")
                text = msg.get("text", {}).get("body", "")
                logger.info("Incoming WhatsApp from %s: %s", from_number, text)
                # Future: route to AI chat handler

    return {"status": "ok"}
