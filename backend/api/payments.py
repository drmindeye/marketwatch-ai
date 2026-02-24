import hashlib
import hmac
import logging

from fastapi import APIRouter, Header, HTTPException, Request, status
from supabase import create_client

from core.config import settings
from models.payment import PaystackEvent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/payments", tags=["payments"])

# Plan amounts in kobo (NGN)
PLAN_AMOUNTS = {
    500_000: "pro",   # ₦5,000
    1_500_000: "elite",  # ₦15,000
}


def _verify_signature(payload: bytes, signature: str) -> bool:
    """HMAC SHA512 verification — rejects any request that fails."""
    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        payload,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(...),
):
    payload = await request.body()

    if not _verify_signature(payload, x_paystack_signature):
        logger.warning("Paystack webhook: invalid signature — rejected")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        event = PaystackEvent.model_validate_json(payload)
    except Exception as exc:
        logger.error("Paystack webhook: payload parse error — %s", exc)
        raise HTTPException(status_code=422, detail="Invalid payload")

    if event.event == "charge.success":
        await _handle_charge_success(event)

    return {"received": True}


async def _handle_charge_success(event: PaystackEvent) -> None:
    data = event.data

    if data.status != "success":
        return

    plan = PLAN_AMOUNTS.get(data.amount)
    if not plan:
        logger.warning("charge.success: unknown amount %d — skipping", data.amount)
        return

    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    # Look up user by email
    result = (
        supabase.table("profiles")
        .select("id")
        .eq("email", data.customer.email)
        .single()
        .execute()
    )

    if not result.data:
        logger.error("charge.success: no profile for %s", data.customer.email)
        return

    user_id = result.data["id"]

    # Update tier
    supabase.table("profiles").update({"tier": plan}).eq("id", user_id).execute()

    # Record subscription
    supabase.table("subscriptions").insert(
        {
            "user_id": user_id,
            "paystack_ref": data.reference,
            "plan": plan,
            "status": "active",
            "amount": data.amount / 100,  # convert kobo → naira
            "currency": data.currency,
        }
    ).execute()

    logger.info(
        "charge.success: upgraded %s to %s (ref: %s)",
        data.customer.email,
        plan,
        data.reference,
    )
