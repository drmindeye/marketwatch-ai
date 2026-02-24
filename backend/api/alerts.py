"""Alert CRUD endpoints — protected by Supabase JWT."""

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field
from supabase import create_client

from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ── Models ─────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    alert_type: str = Field(..., pattern="^(touch|cross|near|zone)$")
    price: float = Field(..., gt=0)
    direction: str | None = Field(default=None, pattern="^(above|below)$")
    pip_buffer: float = Field(default=5.0, gt=0)
    zone_high: float | None = Field(default=None)


class AlertOut(BaseModel):
    id: str
    symbol: str
    alert_type: str
    price: float
    direction: str | None
    pip_buffer: float | None
    zone_high: float | None
    is_active: bool
    triggered_at: str | None
    created_at: str


# ── Auth helper ────────────────────────────────────────────────

def _get_user_id(authorization: str) -> str:
    """Extract and verify user_id from Supabase Bearer JWT."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization.removeprefix("Bearer ")
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    try:
        result = supabase.auth.get_user(token)
        if not result.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return result.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Endpoints ──────────────────────────────────────────────────

@router.get("", response_model=list[AlertOut])
def list_alerts(authorization: str = Header(...)) -> list[AlertOut]:
    """List all alerts for the authenticated user."""
    user_id = _get_user_id(authorization)
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    result = (
        supabase.table("alerts")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    return [AlertOut(**row) for row in (result.data or [])]


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
def create_alert(
    body: AlertCreate,
    authorization: str = Header(...),
) -> AlertOut:
    """Create a new price alert."""
    user_id = _get_user_id(authorization)
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    # Check alert limit for free tier
    profile = (
        supabase.table("profiles")
        .select("tier")
        .eq("id", user_id)
        .single()
        .execute()
    )
    tier = profile.data["tier"] if profile.data else "free"

    if tier == "free":
        count = (
            supabase.table("alerts")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        if (count.count or 0) >= 3:
            raise HTTPException(
                status_code=403,
                detail="Free plan limited to 3 active alerts. Upgrade to Pro for unlimited.",
            )

    if body.alert_type == "zone":
        if body.zone_high is None:
            raise HTTPException(status_code=422, detail="zone_high is required for zone alerts")
        if body.zone_high <= body.price:
            raise HTTPException(status_code=422, detail="zone_high must be greater than price (zone low)")

    row = (
        supabase.table("alerts")
        .insert({
            "user_id": user_id,
            "symbol": body.symbol.upper(),
            "alert_type": body.alert_type,
            "price": body.price,
            "direction": body.direction,
            "pip_buffer": body.pip_buffer,
            "zone_high": body.zone_high,
        })
        .execute()
    )

    return AlertOut(**row.data[0])


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(alert_id: str, authorization: str = Header(...)) -> None:
    """Delete an alert — only the owner can delete."""
    user_id = _get_user_id(authorization)
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    result = (
        supabase.table("alerts")
        .delete()
        .eq("id", alert_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Alert not found")
