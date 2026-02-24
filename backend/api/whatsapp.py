"""WhatsApp Cloud API webhook — verification + full interactive bot interface."""

import asyncio
import logging

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from supabase import create_client

from core.config import settings
from services.ai import chat as ai_chat
from services.whatsapp_service import (
    send_button_message,
    send_list_message,
    send_text_message,
    verify_whatsapp_signature,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

# ── State machine ─────────────────────────────────────────────────────────────
_states: dict[str, dict] = {}
_chat_history: dict[str, list[dict[str, str]]] = {}
FREE_CHAT_LIMIT = 3


def _get_state(phone: str) -> dict:
    return _states.get(phone, {"state": "idle", "data": {}})


def _set_state(phone: str, state: str, data: dict | None = None) -> None:
    _states[phone] = {"state": state, "data": data or {}}


def _clear_state(phone: str) -> None:
    _states.pop(phone, None)


# ── Supabase helpers ──────────────────────────────────────────────────────────

def _db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _get_profile(phone: str) -> dict | None:
    try:
        r = (
            _db().table("profiles")
            .select("*")
            .eq("whatsapp", phone)
            .maybe_single()
            .execute()
        )
        return r.data
    except Exception:
        return None


def _get_alerts(user_id: str) -> list[dict]:
    try:
        r = (
            _db().table("alerts")
            .select("*")
            .eq("user_id", user_id)
            .is_("triggered_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def _get_history(user_id: str, limit: int = 10) -> list[dict]:
    try:
        r = (
            _db().table("alerts")
            .select("*")
            .eq("user_id", user_id)
            .not_.is_("triggered_at", "null")
            .order("triggered_at", desc=True)
            .limit(limit)
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def _create_alert(
    user_id: str,
    symbol: str,
    alert_type: str,
    price: float,
    direction: str | None,
    pip_buffer: float | None,
    zone_high: float | None = None,
) -> bool:
    try:
        _db().table("alerts").insert({
            "user_id": user_id,
            "symbol": symbol.upper(),
            "alert_type": alert_type,
            "price": price,
            "direction": direction,
            "pip_buffer": pip_buffer,
            "zone_high": zone_high,
        }).execute()
        return True
    except Exception as e:
        logger.error("WA create alert error: %s", e)
        return False


def _delete_alert(alert_id: str, user_id: str) -> bool:
    try:
        _db().table("alerts").delete().eq("id", alert_id).eq("user_id", user_id).execute()
        return True
    except Exception:
        return False


def _count_active_alerts(user_id: str) -> int:
    try:
        r = (
            _db().table("alerts")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .is_("triggered_at", "null")
            .execute()
        )
        return r.count or 0
    except Exception:
        return 0


def _pip_size(symbol: str) -> float:
    s = symbol.upper()
    if "JPY" in s:
        return 0.01
    if any(x in s for x in ("BTC", "ETH", "XAU", "GOLD")):
        return 0.01
    return 0.0001


# ── Menu senders ──────────────────────────────────────────────────────────────

async def _send_main_menu(phone: str, greeting: str = "What would you like to do?") -> None:
    await send_list_message(
        phone,
        f"🏠 *Main Menu*\n{greeting}",
        "Open Menu",
        [{
            "title": "Features",
            "rows": [
                {"id": "menu_alerts", "title": "🔔 Alerts", "description": "Create, view and delete price alerts"},
                {"id": "menu_calc", "title": "🧮 Calculator", "description": "Risk/Reward, Position Size, Pip Value"},
                {"id": "menu_history", "title": "📜 History", "description": "View your triggered alerts"},
                {"id": "menu_settings", "title": "⚙️ Settings", "description": "View your account settings"},
                {"id": "menu_chat", "title": "💬 AI Chat", "description": "Ask market questions"},
            ],
        }],
    )


async def _send_alerts_menu(phone: str) -> None:
    await send_button_message(
        phone,
        "🔔 *Alerts Menu*\nWhat would you like to do?",
        [
            ("alert_create", "➕ Create Alert"),
            ("alert_view", "📋 View Alerts"),
            ("alert_delete", "🗑 Delete Alert"),
        ],
    )


async def _send_calc_menu(phone: str) -> None:
    await send_list_message(
        phone,
        "🧮 *Calculator*\nChoose a tool:",
        "Choose Tool",
        [{
            "title": "Tools",
            "rows": [
                {"id": "calc_rr", "title": "⚖️ Risk/Reward", "description": "Calculate R:R ratio"},
                {"id": "calc_ps", "title": "📐 Position Size", "description": "Calculate lot size"},
                {"id": "calc_pip", "title": "📏 Pip Calculator", "description": "Count pips between prices"},
            ],
        }],
    )


async def _require_linked(phone: str) -> dict | None:
    profile = _get_profile(phone)
    if not profile:
        await send_text_message(
            phone,
            "⚠️ Your WhatsApp is not linked to a MarketWatch account.\n\n"
            "Send: *link your@email.com* to connect your account.",
        )
        return None
    return profile


# ── Main message router ───────────────────────────────────────────────────────

async def _handle_wa_message(phone: str, text: str, msg_type: str = "text") -> None:
    """Route an incoming WhatsApp message to the right handler."""
    text = text.strip()
    lower = text.lower()

    # Link account: "link email@example.com"
    if lower.startswith("link ") and "@" in text:
        email = text.split(" ", 1)[1].strip().lower()
        try:
            r = _db().table("profiles").update({"whatsapp": phone}).eq("email", email).execute()
            if r.data:
                profile = r.data[0]
                name = profile.get("full_name") or profile.get("email")
                await send_text_message(
                    phone,
                    f"✅ Account linked!\n\nWelcome, {name}!\n"
                    "Your WhatsApp is now connected. Send *menu* to get started.",
                )
            else:
                await send_text_message(phone, "❌ No account found with that email. Make sure you've signed up first.")
        except Exception:
            await send_text_message(phone, "⚠️ Something went wrong. Please try again.")
        return

    # Menu triggers
    if lower in ("menu", "hi", "hello", "start", "/start", "/menu"):
        _clear_state(phone)
        profile = _get_profile(phone)
        name = profile.get("full_name") or profile.get("email", "Trader") if profile else "Trader"
        await _send_main_menu(phone, f"Welcome back, {name}!")
        return

    if lower == "help":
        await send_text_message(
            phone,
            "🤖 *MarketWatch AI — WhatsApp Bot*\n\n"
            "Send *menu* to open the main menu\n"
            "Send *link your@email.com* to link your account\n"
            "Send *cancel* to cancel current action\n\n"
            "Or just ask any market question!",
        )
        return

    if lower == "cancel":
        _clear_state(phone)
        await send_text_message(phone, "❌ Cancelled. Send *menu* to start over.")
        return

    # Interactive replies (button/list selections)
    if msg_type in ("button_reply", "list_reply"):
        await _handle_selection(phone, text)
        return

    # State machine for multi-step flows
    state = _get_state(phone)
    s = state["state"]
    d = state["data"]

    if s != "idle" and s != "chat_mode":
        await _handle_state_input(phone, text, s, d)
        return

    # AI chat fallback
    await _handle_ai_chat(phone, text)


async def _handle_selection(phone: str, selection_id: str) -> None:
    """Handle button/list reply selections."""

    # Main menu selections
    if selection_id == "menu_alerts":
        _clear_state(phone)
        await _send_alerts_menu(phone)

    elif selection_id == "menu_calc":
        _clear_state(phone)
        await _send_calc_menu(phone)

    elif selection_id == "menu_history":
        profile = await _require_linked(phone)
        if not profile:
            return
        history = _get_history(profile["id"])
        if not history:
            await send_text_message(phone, "📭 No triggered alerts yet.")
            return
        lines = ["📜 *Recent Triggered Alerts*\n"]
        for a in history:
            emoji = {"touch": "🎯", "cross": "⚡", "near": "📍"}.get(a["alert_type"], "🔔")
            lines.append(f"{emoji} {a['symbol']} — {a['alert_type']} @ {a['price']}")
        await send_text_message(phone, "\n".join(lines))

    elif selection_id == "menu_settings":
        profile = await _require_linked(phone)
        if not profile:
            return
        wa = profile.get("whatsapp") or "Not set"
        tier = profile.get("tier", "free")
        await send_text_message(
            phone,
            f"⚙️ *Your Settings*\n\n"
            f"📧 Email: {profile.get('email', 'N/A')}\n"
            f"🏅 Plan: {tier.upper()}\n"
            f"📱 WhatsApp: {wa}\n\n"
            "Send *menu* to go back.",
        )

    elif selection_id == "menu_chat":
        _set_state(phone, "chat_mode")
        await send_text_message(
            phone,
            "💬 *AI Chat Mode*\n\nAsk me any Forex or market question.\nSend *menu* to return to main menu.",
        )

    # Alert actions
    elif selection_id == "alert_create":
        profile = await _require_linked(phone)
        if not profile:
            return
        tier = profile.get("tier", "free")
        limit = 3 if tier == "free" else 20
        count = _count_active_alerts(profile["id"])
        if count >= limit:
            await send_text_message(
                phone,
                f"⚠️ Alert limit reached ({count}/{limit} for {tier} plan).\n"
                "Delete an alert or upgrade to create more.",
            )
            return
        _set_state(phone, "alert_symbol", {"user_id": profile["id"]})
        await send_text_message(phone, "📝 *Create Alert — Step 1/4*\n\nEnter the trading symbol:\n(e.g. EURUSD, BTCUSD, XAUUSD)")

    elif selection_id == "alert_view":
        profile = await _require_linked(phone)
        if not profile:
            return
        alerts = _get_alerts(profile["id"])
        if not alerts:
            await send_text_message(phone, "📭 No active alerts.")
            return
        lines = ["📋 *Your Active Alerts*\n"]
        for a in alerts:
            emoji = {"touch": "🎯", "cross": "⚡", "near": "📍"}.get(a["alert_type"], "🔔")
            direction = f" ({a['direction']})" if a.get("direction") else ""
            pip_buf = f" ±{a['pip_buffer']}pip" if a.get("pip_buffer") else ""
            lines.append(f"{emoji} {a['symbol']} {a['alert_type']}{direction} @ {a['price']}{pip_buf}")
        await send_text_message(phone, "\n".join(lines))

    elif selection_id == "alert_delete":
        profile = await _require_linked(phone)
        if not profile:
            return
        alerts = _get_alerts(profile["id"])
        if not alerts:
            await send_text_message(phone, "📭 No active alerts to delete.")
            return
        # Store alerts in state for deletion flow
        _set_state(phone, "alert_delete_select", {"user_id": profile["id"], "alerts": alerts})
        lines = ["🗑 *Delete Alert*\n\nReply with the number of the alert to delete:\n"]
        for i, a in enumerate(alerts, 1):
            emoji = {"touch": "🎯", "cross": "⚡", "near": "📍"}.get(a["alert_type"], "🔔")
            lines.append(f"{i}. {emoji} {a['symbol']} {a['alert_type']} @ {a['price']}")
        await send_text_message(phone, "\n".join(lines))

    # Calculator
    elif selection_id == "calc_rr":
        _set_state(phone, "calc_rr_entry")
        await send_text_message(phone, "⚖️ *Risk/Reward Calculator*\n\n*Step 1/3* — Enter your entry price:")

    elif selection_id == "calc_ps":
        _set_state(phone, "calc_ps_balance")
        await send_text_message(phone, "📐 *Position Size Calculator*\n\n*Step 1/4* — Enter your account balance (USD):")

    elif selection_id == "calc_pip":
        _set_state(phone, "calc_pip_symbol")
        await send_text_message(phone, "📏 *Pip Calculator*\n\n*Step 1/3* — Enter the symbol (e.g. EURUSD):")


async def _handle_state_input(phone: str, text: str, s: str, d: dict) -> None:
    """Handle text inputs during multi-step flows."""

    # Alert type selection
    if s == "alert_symbol":
        symbol = text.upper().replace("/", "").replace("-", "").replace(" ", "")
        _set_state(phone, "alert_type", {**d, "symbol": symbol})
        await send_list_message(
            phone,
            f"Symbol: {symbol}\n\n*Step 2/4* — Select alert type:",
            "Select Type",
            [{
                "title": "Alert Types",
                "rows": [
                    {"id": "type_touch", "title": "🎯 Touch", "description": "Triggers when price hits a level"},
                    {"id": "type_cross", "title": "⚡ Cross", "description": "Triggers when price crosses a level"},
                    {"id": "type_near", "title": "📍 Near", "description": "Triggers within X pips of a level"},
                    {"id": "type_zone", "title": "📦 Zone", "description": "Triggers when price enters a zone"},
                ],
            }],
        )
        return

    if s == "alert_type":
        t = text.lower()
        if t not in ("touch", "cross", "near", "zone"):
            await send_text_message(phone, "Please reply with: touch, cross, near, or zone")
            return
        _set_state(phone, "alert_price", {**d, "alert_type": t})
        label = "zone low (lower bound)" if t == "zone" else "target price"
        await send_text_message(phone, f"Type: {t}\n\n*Step 3/4* — Enter the {label}:")
        return

    if s == "alert_price":
        try:
            price = float(text)
        except ValueError:
            await send_text_message(phone, "❌ Invalid price. Enter a number (e.g. 1.08500):")
            return
        alert_type = d.get("alert_type")
        if alert_type == "cross":
            _set_state(phone, "alert_direction", {**d, "price": price})
            await send_button_message(
                phone,
                f"Target: {price}\n\nWhich direction should price come from?",
                [("dir_above", "📈 Above"), ("dir_below", "📉 Below")],
            )
        elif alert_type == "near":
            _set_state(phone, "alert_pip_buffer", {**d, "price": price})
            await send_text_message(phone, f"Target: {price}\n\nEnter pip buffer (e.g. 5):")
        elif alert_type == "zone":
            _set_state(phone, "alert_zone_high", {**d, "price": price})
            await send_text_message(phone, f"Zone Low: {price}\n\n*Step 4/4* — Enter the zone high (upper bound):")
        else:
            ok = _create_alert(d["user_id"], d["symbol"], alert_type, price, None, None)
            _clear_state(phone)
            if ok:
                await send_text_message(phone, f"✅ Alert Created!\n\n🎯 {d['symbol']} touch alert at {price}\n\nSend *menu* to manage alerts.")
            else:
                await send_text_message(phone, "❌ Failed to create alert.")
        return

    if s == "alert_zone_high":
        try:
            zone_high = float(text)
        except ValueError:
            await send_text_message(phone, "❌ Enter a valid price:")
            return
        if zone_high <= d["price"]:
            await send_text_message(phone, f"❌ Zone high must be above zone low ({d['price']}):")
            return
        ok = _create_alert(d["user_id"], d["symbol"], "zone", d["price"], None, None, zone_high)
        _clear_state(phone)
        msg = (
            f"✅ Alert Created!\n\n📦 {d['symbol']} zone alert\n"
            f"Triggers when price enters {d['price']} – {zone_high}"
            if ok else "❌ Failed to create alert."
        )
        await send_text_message(phone, msg + "\n\nSend *menu* to manage alerts.")
        return

    if s == "alert_direction":
        t = text.lower()
        if t not in ("above", "below"):
            await send_button_message(phone, "Select direction:", [("dir_above", "📈 Above"), ("dir_below", "📉 Below")])
            return
        ok = _create_alert(d["user_id"], d["symbol"], d["alert_type"], d["price"], t, None)
        _clear_state(phone)
        msg = f"✅ Alert Created!\n\n⚡ {d['symbol']} cross alert at {d['price']} from {t}" if ok else "❌ Failed to create alert."
        await send_text_message(phone, msg + "\n\nSend *menu* to manage alerts.")
        return

    if s == "alert_pip_buffer":
        try:
            pip_buffer = float(text)
        except ValueError:
            await send_text_message(phone, "❌ Enter a valid number (e.g. 5):")
            return
        ok = _create_alert(d["user_id"], d["symbol"], d["alert_type"], d["price"], None, pip_buffer)
        _clear_state(phone)
        msg = f"✅ Alert Created!\n\n📍 {d['symbol']} near alert at {d['price']} ±{pip_buffer} pips" if ok else "❌ Failed to create alert."
        await send_text_message(phone, msg + "\n\nSend *menu* to manage alerts.")
        return

    if s == "alert_delete_select":
        try:
            idx = int(text) - 1
            alerts = d.get("alerts", [])
            if idx < 0 or idx >= len(alerts):
                raise ValueError
            alert = alerts[idx]
        except (ValueError, IndexError):
            await send_text_message(phone, f"❌ Enter a number between 1 and {len(d.get('alerts', []))}:")
            return
        ok = _delete_alert(alert["id"], d["user_id"])
        _clear_state(phone)
        emoji = {"touch": "🎯", "cross": "⚡", "near": "📍"}.get(alert["alert_type"], "🔔")
        msg = f"✅ Deleted: {emoji} {alert['symbol']} {alert['alert_type']} @ {alert['price']}" if ok else "❌ Failed to delete alert."
        await send_text_message(phone, msg + "\n\nSend *menu* to continue.")
        return

    # Alert type / direction via button_reply text
    if s == "alert_type" and text.lower() in ("type_touch", "type_cross", "type_near"):
        await _handle_selection(phone, text.lower())
        return

    if s == "alert_direction" and text.lower() in ("dir_above", "dir_below"):
        await _handle_selection(phone, text.lower())
        return

    # Risk/Reward
    if s == "calc_rr_entry":
        try:
            _set_state(phone, "calc_rr_sl", {**d, "entry": float(text)})
            await send_text_message(phone, "*Step 2/3* — Enter your stop loss price:")
        except ValueError:
            await send_text_message(phone, "❌ Enter a valid price:")
        return

    if s == "calc_rr_sl":
        try:
            _set_state(phone, "calc_rr_tp", {**d, "sl": float(text)})
            await send_text_message(phone, "*Step 3/3* — Enter your take profit price:")
        except ValueError:
            await send_text_message(phone, "❌ Enter a valid price:")
        return

    if s == "calc_rr_tp":
        try:
            tp = float(text)
            entry, sl = d["entry"], d["sl"]
            risk = abs(entry - sl)
            reward = abs(tp - entry)
            ratio = round(reward / risk, 2) if risk > 0 else 0
            pip = 0.0001
            _clear_state(phone)
            await send_text_message(
                phone,
                f"⚖️ *Risk/Reward Result*\n\n"
                f"Entry: {entry}  |  SL: {sl}  |  TP: {tp}\n\n"
                f"Risk: {round(risk/pip,1)} pips\n"
                f"Reward: {round(reward/pip,1)} pips\n"
                f"Ratio: 1:{ratio}\n\n"
                "Send *calc* to run another calculation.",
            )
        except ValueError:
            await send_text_message(phone, "❌ Enter a valid price:")
        return

    # Position size
    if s == "calc_ps_balance":
        try:
            _set_state(phone, "calc_ps_risk", {**d, "balance": float(text)})
            await send_text_message(phone, "*Step 2/4* — Enter your risk % per trade (e.g. 1 or 2):")
        except ValueError:
            await send_text_message(phone, "❌ Enter a valid number:")
        return

    if s == "calc_ps_risk":
        try:
            _set_state(phone, "calc_ps_sl_pips", {**d, "risk_pct": float(text)})
            await send_text_message(phone, "*Step 3/4* — Enter stop loss in pips:")
        except ValueError:
            await send_text_message(phone, "❌ Enter a valid number:")
        return

    if s == "calc_ps_sl_pips":
        try:
            _set_state(phone, "calc_ps_pip_val", {**d, "sl_pips": float(text)})
            await send_text_message(phone, "*Step 4/4* — Enter pip value per standard lot (e.g. 10 for EURUSD):")
        except ValueError:
            await send_text_message(phone, "❌ Enter a valid number:")
        return

    if s == "calc_ps_pip_val":
        try:
            pip_val = float(text)
            risk_amt = round(d["balance"] * (d["risk_pct"] / 100), 2)
            lots = round(risk_amt / (d["sl_pips"] * pip_val), 4) if d["sl_pips"] * pip_val > 0 else 0
            units = int(lots * 100_000)
            _clear_state(phone)
            await send_text_message(
                phone,
                f"📐 *Position Size Result*\n\n"
                f"Balance: ${d['balance']:,.2f}  |  Risk: {d['risk_pct']}%\n"
                f"Stop Loss: {d['sl_pips']} pips\n\n"
                f"Lot Size: {lots}\n"
                f"Units: {units:,}\n"
                f"Risk Amount: ${risk_amt:,.2f}\n\n"
                "Send *calc* to run another calculation.",
            )
        except ValueError:
            await send_text_message(phone, "❌ Enter a valid number:")
        return

    # Pip calculator
    if s == "calc_pip_symbol":
        _set_state(phone, "calc_pip_p1", {**d, "symbol": text.upper()})
        await send_text_message(phone, f"Symbol: {text.upper()}\n\n*Step 2/3* — Enter price from:")
        return

    if s == "calc_pip_p1":
        try:
            _set_state(phone, "calc_pip_p2", {**d, "p1": float(text)})
            await send_text_message(phone, "*Step 3/3* — Enter price to:")
        except ValueError:
            await send_text_message(phone, "❌ Enter a valid price:")
        return

    if s == "calc_pip_p2":
        try:
            p2 = float(text)
            p1 = d["p1"]
            symbol = d["symbol"]
            diff = p2 - p1
            pips = round(abs(diff) / _pip_size(symbol), 1)
            direction = "up 📈" if diff > 0 else "down 📉"
            _clear_state(phone)
            await send_text_message(
                phone,
                f"📏 *Pip Calculator Result*\n\n"
                f"Symbol: {symbol}\n"
                f"{p1} → {p2}\n\n"
                f"Movement: {pips} pips {direction}\n\n"
                "Send *calc* to run another calculation.",
            )
        except ValueError:
            await send_text_message(phone, "❌ Enter a valid price:")
        return


async def _handle_ai_chat(phone: str, text: str) -> None:
    profile = _get_profile(phone)
    tier = profile.get("tier", "free") if profile else "free"
    history = _chat_history.get(phone, [])
    user_msgs = [m for m in history if m["role"] == "user"]

    if tier == "free" and len(user_msgs) >= FREE_CHAT_LIMIT:
        await send_text_message(
            phone,
            f"⚠️ You've used your {FREE_CHAT_LIMIT} free AI questions this session.\n\n"
            "Upgrade to PRO for unlimited AI chat! Visit marketwatch-ai to upgrade.",
        )
        return

    history.append({"role": "user", "content": text})
    _chat_history[phone] = history

    try:
        reply = await asyncio.to_thread(ai_chat, history)
        history.append({"role": "assistant", "content": reply})
        _chat_history[phone] = history[-20:]
        await send_text_message(phone, reply)
    except Exception as exc:
        logger.error("WA AI chat error: %s", exc)
        await send_text_message(phone, "⚠️ AI is temporarily unavailable. Please try again shortly.")


# ── Webhook endpoints ─────────────────────────────────────────────────────────

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
    """Receive and route incoming WhatsApp messages."""
    payload = await request.body()

    if x_hub_signature_256 and not verify_whatsapp_signature(payload, x_hub_signature_256):
        logger.warning("WhatsApp webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON")

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                phone = msg.get("from", "")
                msg_type = msg.get("type", "text")

                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "").strip()
                    if text:
                        asyncio.create_task(_handle_wa_message(phone, text, "text"))

                elif msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    i_type = interactive.get("type")
                    if i_type == "button_reply":
                        sel_id = interactive["button_reply"]["id"]
                        asyncio.create_task(_handle_wa_message(phone, sel_id, "button_reply"))
                    elif i_type == "list_reply":
                        sel_id = interactive["list_reply"]["id"]
                        asyncio.create_task(_handle_wa_message(phone, sel_id, "list_reply"))

    return {"status": "ok"}
