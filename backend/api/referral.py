"""Referral system endpoints."""

import logging

from fastapi import APIRouter, Header, HTTPException
from supabase import create_client

from api.alerts import _get_user_id
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/referral", tags=["referral"])


def _db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


@router.get("")
def get_referral(authorization: str = Header(...)) -> dict:
    """Return the current user's referral code, count, and referral link."""
    user_id = _get_user_id(authorization)
    db = _db()

    profile = (
        db.table("profiles")
        .select("referral_code, referral_count")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    code: str = profile.data.get("referral_code") or ""
    count: int = profile.data.get("referral_count") or 0

    return {
        "code": code,
        "count": count,
        "link": f"{settings.FRONTEND_URL}/signup?ref={code}",
        "reward": "Earn 1 week of Pro free for every friend who upgrades.",
    }


@router.post("/claim")
def claim_referral(body: dict, authorization: str = Header(...)) -> dict:
    """Link the signing-up user to a referrer by code.

    Called from the auth callback when a ?ref=CODE param is present.
    Safe to call multiple times — ignores if referred_by already set.
    """
    user_id = _get_user_id(authorization)
    code: str = (body.get("code") or "").upper().strip()
    if not code:
        raise HTTPException(status_code=400, detail="code is required")

    db = _db()

    # Don't overwrite an existing referral
    existing = (
        db.table("profiles")
        .select("referred_by, referral_code")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if existing.data and existing.data.get("referred_by"):
        return {"ok": True, "message": "already claimed"}

    # Prevent self-referral
    if existing.data and existing.data.get("referral_code") == code:
        raise HTTPException(status_code=400, detail="Cannot use your own referral code")

    # Find referrer
    referrer = (
        db.table("profiles")
        .select("id")
        .eq("referral_code", code)
        .maybe_single()
        .execute()
    )
    if not referrer.data:
        raise HTTPException(status_code=404, detail="Referral code not found")

    referrer_id = referrer.data["id"]
    db.table("profiles").update({"referred_by": referrer_id}).eq("id", user_id).execute()
    return {"ok": True}
