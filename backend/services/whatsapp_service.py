"""WhatsApp Cloud API (Meta Graph API) — alerts, interactive menus, bot interface."""

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


async def _post(url: str, payload: dict) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            )
            resp.raise_for_status()
            return True
    except httpx.HTTPStatusError as exc:
        logger.error("WhatsApp API error: %s", exc.response.text)
        return False
    except Exception as exc:
        logger.error("WhatsApp send error: %s", exc)
        return False


async def send_text_message(phone: str, text: str) -> bool:
    """Send a plain text message."""
    url = f"{GRAPH_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    return await _post(url, {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    })


async def send_button_message(phone: str, body: str, buttons: list[tuple[str, str]]) -> bool:
    """Send interactive button message (max 3 buttons).
    buttons = [(id, label), ...]
    """
    url = f"{GRAPH_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    return await _post(url, {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": bid, "title": label[:20]}}
                    for bid, label in buttons[:3]
                ]
            },
        },
    })


async def send_list_message(
    phone: str,
    body: str,
    button_label: str,
    sections: list[dict],
) -> bool:
    """Send interactive list message.
    sections = [{"title": "...", "rows": [{"id": "...", "title": "...", "description": "..."}]}]
    """
    url = f"{GRAPH_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    return await _post(url, {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": button_label[:20],
                "sections": sections,
            },
        },
    })


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
    Named parameters (Meta-approved):
      {{symbol}}        = trading pair / ticker
      {{alert_type}}    = touch / cross / near
      {{current_price}} = current market price
      {{target_level}}  = alert target price
      {{ai_summary}}    = AI market context
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
                        {"type": "text", "parameter_name": "symbol", "text": symbol},
                        {"type": "text", "parameter_name": "alert_type", "text": alert_type.upper()},
                        {"type": "text", "parameter_name": "current_price", "text": f"{price:.5f}"},
                        {"type": "text", "parameter_name": "target_level", "text": f"{target:.5f}"},
                        {"type": "text", "parameter_name": "ai_summary", "text": ai_summary},
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
        logger.error("WhatsApp send failed %s: %s", phone, exc.response.text)
        return False
    except Exception as exc:
        logger.error("WhatsApp send error %s: %s", phone, exc)
        return False
