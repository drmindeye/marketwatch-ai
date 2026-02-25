"""Email alert delivery via Resend API.

Set RESEND_API_KEY in environment to enable.
From address: alerts@yourdomain.com (must be a verified Resend domain).
"""

import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"
FROM_ADDRESS = "MarketWatch AI <alerts@marketwatchai.com>"


async def send_alert_email(
    to: str,
    symbol: str,
    alert_type: str,
    price: float,
    target: float,
    ai_summary: str,
) -> None:
    """Send a price alert email. No-ops silently if RESEND_API_KEY is not set."""
    if not settings.RESEND_API_KEY:
        logger.debug("RESEND_API_KEY not set — skipping email alert for %s", to)
        return

    type_labels = {
        "touch": "touched",
        "cross": "crossed",
        "near": "is near",
        "zone": "entered your zone at",
    }
    verb = type_labels.get(alert_type, "hit")

    subject = f"🔔 {symbol} Alert — {alert_type.capitalize()} @ {price:.5f}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px">
      <h2 style="color:#10b981;margin:0 0 8px">MarketWatch AI Alert</h2>
      <p style="color:#6b7280;margin:0 0 24px;font-size:14px">Price alert triggered</p>

      <div style="background:#111;border-radius:12px;padding:20px;margin-bottom:20px">
        <p style="font-size:22px;font-weight:700;color:#fff;margin:0">{symbol}</p>
        <p style="color:#9ca3af;font-size:14px;margin:4px 0 16px">
          {symbol} {verb} <strong style="color:#fff">{target:.5f}</strong>
        </p>
        <p style="font-size:16px;color:#10b981;font-weight:600;margin:0">
          Current price: {price:.5f}
        </p>
      </div>

      <div style="background:#111;border-radius:12px;padding:20px;margin-bottom:24px">
        <p style="color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:.05em;margin:0 0 8px">
          AI Market Context
        </p>
        <p style="color:#d1d5db;font-size:14px;line-height:1.6;margin:0">{ai_summary}</p>
      </div>

      <a href="{settings.FRONTEND_URL}/dashboard/alerts"
         style="display:inline-block;background:#10b981;color:#000;font-weight:600;
                padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px">
        Manage Alerts →
      </a>

      <p style="color:#374151;font-size:12px;margin-top:24px">
        You're receiving this because you have no Telegram or WhatsApp linked.<br>
        <a href="{settings.FRONTEND_URL}/dashboard/settings" style="color:#10b981">
          Link Telegram to get faster alerts.
        </a>
      </p>
    </div>
    """

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                RESEND_URL,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={"from": FROM_ADDRESS, "to": [to], "subject": subject, "html": html},
            )
        if resp.status_code not in (200, 201):
            logger.error("Resend email failed (%s): %s", resp.status_code, resp.text)
        else:
            logger.info("Email alert sent to %s for %s", to, symbol)
    except Exception as exc:
        logger.error("Email send error: %s", exc)
