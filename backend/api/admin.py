"""Admin endpoints — promote users, platform stats."""

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from supabase import create_client

from api.alerts import _get_user_id
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _require_admin(authorization: str) -> str:
    user_id = _get_user_id(authorization)
    db = _db()
    try:
        profile = db.table("profiles").select("is_admin").eq("id", user_id).single().execute()
    except Exception as exc:
        logger.error("Admin profile lookup failed: %s", exc)
        raise HTTPException(status_code=403, detail="Admin access required")
    if not (profile.data or {}).get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id


def _find_profile(db, identifier: str) -> dict | None:
    """Find a profile by email, UUID, or referral code."""
    # 1. Try email
    try:
        r = db.table("profiles").select("id, email, tier").eq("email", identifier).maybe_single().execute()
        if r.data:
            return r.data
    except Exception as exc:
        logger.warning("Email lookup failed for %r: %s", identifier, exc)

    # 2. Try UUID (only if it looks like one to avoid Postgres cast errors)
    if _UUID_RE.match(identifier):
        try:
            r = db.table("profiles").select("id, email, tier").eq("id", identifier).maybe_single().execute()
            if r.data:
                return r.data
        except Exception as exc:
            logger.warning("UUID lookup failed for %r: %s", identifier, exc)

    # 3. Try referral code
    try:
        r = db.table("profiles").select("id, email, tier").eq("referral_code", identifier.upper()).maybe_single().execute()
        if r.data:
            return r.data
    except Exception as exc:
        logger.warning("Referral code lookup failed for %r: %s", identifier, exc)

    return None


class PromoteBody(BaseModel):
    identifier: str  # email, user UUID, or referral code


@router.post("/promote")
def promote_user(body: PromoteBody, authorization: str = Header(...)) -> dict:
    """Promote a user to Pro tier by email, UUID, or referral code."""
    _require_admin(authorization)
    db = _db()

    identifier = body.identifier.strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="Identifier is required")

    target = _find_profile(db, identifier)
    if not target:
        raise HTTPException(status_code=404, detail=f"No user found for: {identifier!r}")

    if target["tier"] == "pro":
        return {"ok": True, "message": f"{target['email']} is already Pro"}

    # Update profile tier
    try:
        db.table("profiles").update({"tier": "pro"}).eq("id", target["id"]).execute()
    except Exception as exc:
        logger.error("Profile tier update failed for %s: %s", target["id"], exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update user tier: {exc}")

    # Insert subscription record for history — non-fatal if it fails
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

    logger.info("Admin promoted %s (%s) to Pro", target["email"], target["id"])
    return {"ok": True, "message": f"{target['email']} promoted to Pro ✅"}
