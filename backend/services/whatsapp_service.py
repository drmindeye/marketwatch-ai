"""WhatsApp Cloud API (Meta Graph API) — direct integration, no SDK."""

import hashlib
import hmac
import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.facebook.com/v19.0"


def verify_whatsapp_signature(payload: bytes, signature: str) -> bool:
    """Verify Meta webhook signature (HMAC SHA256, prefix 'sha256=')."""
    expected = hmac.new(
        settings.WHATSAPP_ACCESS_TOKEN.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    received = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


async def send_alert_template(
    phone: str,
    symbol: str,
    alert_type: str,
    price: float,
    target: float,
    ai_summary: str,
) -> bool:
    """Send a pre-approved WhatsApp template message for an alert trigger.

    Template name: 'market_alert'
    Parameters:
      {{1}} = symbol
      {{2}} = alert_type
      {{3}} = price
      {{4}} = target
      {{5}} = AI summary
    """
    url = f"{GRAPH_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "market_alert",
            "language": {"code": "en_US"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": symbol},
                        {"type": "text", "text": alert_type.upper()},
                        {"type": "text", "text": f"{price:.5f}"},
                        {"type": "text", "text": f"{target:.5f}"},
                        {"type": "text", "text": ai_summary},
                    ],
                }
            ],
        },
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            )
            resp.raise_for_status()
            logger.info("WhatsApp alert sent to %s for %s", phone, symbol)
            return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "WhatsApp send failed %s: %s", phone, exc.response.text
        )
        return False
    except Exception as exc:
        logger.error("WhatsApp send error %s: %s", phone, exc)
        return False


async def send_text_message(phone: str, text: str) -> bool:
    """Send a plain text WhatsApp message (for session windows)."""
    url = f"{GRAPH_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            )
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.error("WhatsApp text send error: %s", exc)
        return False
