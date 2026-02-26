"""Admin endpoints — promote users, platform stats."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from supabase import create_client

from api.alerts import _get_user_id
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


def _db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _require_admin(authorization: str) -> str:
    user_id = _get_user_id(authorization)
    db = _db()
    profile = db.table("profiles").select("is_admin").eq("id", user_id).single().execute()
    if not (profile.data or {}).get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id


class PromoteBody(BaseModel):
    identifier: str  # email or user UUID


@router.post("/promote")
def promote_user(body: PromoteBody, authorization: str = Header(...)) -> dict:
    """Promote a user to Pro tier by email or UUID."""
    _require_admin(authorization)
    db = _db()

    identifier = body.identifier.strip()

    # Try by email first, then by UUID
    result = (
        db.table("profiles")
        .select("id, email, tier")
        .eq("email", identifier)
        .maybe_single()
        .execute()
    )
    if not result.data:
        result = (
            db.table("profiles")
            .select("id, email, tier")
            .eq("id", identifier)
            .maybe_single()
            .execute()
        )
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    target = result.data
    if target["tier"] == "pro":
        return {"ok": True, "message": f"{target['email']} is already Pro"}

    db.table("profiles").update({"tier": "pro"}).eq("id", target["id"]).execute()

    # Insert subscription record for history — non-fatal if it fails
    # (paystack_ref must be globally unique; use timestamp to avoid conflicts)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    try:
        db.table("subscriptions").insert({
            "user_id": target["id"],
            "paystack_ref": f"admin_grant_{target['id'][:8]}_{ts}",
            "plan": "pro",
            "status": "active",
            "amount": 0,
            "currency": "NGN",
        }).execute()
    except Exception as sub_exc:
        logger.warning("Subscription record insert failed (non-fatal): %s", sub_exc)

    logger.info("Admin promoted %s to Pro", target["email"])
    return {"ok": True, "message": f"{target['email']} promoted to Pro"}
