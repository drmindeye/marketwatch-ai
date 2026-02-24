"""Telegram bot — full menu interface with alerts, calculator, history, settings."""

import asyncio
import logging
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from fastapi import APIRouter, Request
from supabase import create_client

from core.config import settings
from services.ai import chat as ai_chat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/telegram", tags=["telegram"])

_dp = Dispatcher()
_bot: Bot | None = None

# ── State machine ─────────────────────────────────────────────────────────────
# {telegram_id: {"state": str, "data": dict}}
_states: dict[str, dict] = {}
_chat_history: dict[str, list[dict[str, str]]] = {}
FREE_CHAT_LIMIT = 3


def _get_state(tid: str) -> dict:
    return _states.get(tid, {"state": "idle", "data": {}})


def _set_state(tid: str, state: str, data: dict | None = None) -> None:
    _states[tid] = {"state": state, "data": data or {}}


def _clear_state(tid: str) -> None:
    _states.pop(tid, None)


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    return _bot


# ── Supabase helpers ──────────────────────────────────────────────────────────

def _db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _get_profile(telegram_id: str) -> dict | None:
    try:
        r = (
            _db().table("profiles")
            .select("*")
            .eq("telegram_id", telegram_id)
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
) -> bool:
    try:
        _db().table("alerts").insert({
            "user_id": user_id,
            "symbol": symbol.upper(),
            "alert_type": alert_type,
            "price": price,
            "direction": direction,
            "pip_buffer": pip_buffer,
        }).execute()
        return True
    except Exception as e:
        logger.error("Create alert error: %s", e)
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


# ── Keyboards ─────────────────────────────────────────────────────────────────

def _main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔔 Alerts", callback_data="menu_alerts"),
            InlineKeyboardButton(text="🧮 Calculator", callback_data="menu_calc"),
        ],
        [
            InlineKeyboardButton(text="📜 History", callback_data="menu_history"),
            InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings"),
        ],
        [InlineKeyboardButton(text="💬 AI Chat", callback_data="menu_chat")],
    ])


def _alerts_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Create Alert", callback_data="alert_create")],
        [InlineKeyboardButton(text="📋 View Alerts", callback_data="alert_view")],
        [InlineKeyboardButton(text="🗑 Delete Alert", callback_data="alert_delete")],
        [InlineKeyboardButton(text="◀️ Main Menu", callback_data="menu_main")],
    ])


def _alert_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Touch", callback_data="type_touch"),
            InlineKeyboardButton(text="⚡ Cross", callback_data="type_cross"),
            InlineKeyboardButton(text="📍 Near", callback_data="type_near"),
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="menu_alerts")],
    ])


def _direction_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📈 Above", callback_data="dir_above"),
            InlineKeyboardButton(text="📉 Below", callback_data="dir_below"),
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="menu_alerts")],
    ])


def _calc_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚖️ Risk / Reward", callback_data="calc_rr")],
        [InlineKeyboardButton(text="📐 Position Size", callback_data="calc_ps")],
        [InlineKeyboardButton(text="📏 Pip Calculator", callback_data="calc_pip")],
        [InlineKeyboardButton(text="◀️ Main Menu", callback_data="menu_main")],
    ])


def _back_alerts_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Alerts Menu", callback_data="menu_alerts")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")],
    ])


def _back_calc_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Calculator", callback_data="menu_calc")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")],
    ])


def _back_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")],
    ])


# ── Calculator helpers ────────────────────────────────────────────────────────

def _pip_size(symbol: str) -> float:
    s = symbol.upper()
    if "JPY" in s:
        return 0.01
    if any(x in s for x in ("BTC", "ETH", "XAU", "GOLD")):
        return 0.01
    return 0.0001


# ── Require linked account ────────────────────────────────────────────────────

async def _require_linked(bot: Bot, chat_id: int, tid: str) -> dict | None:
    profile = _get_profile(tid)
    if not profile:
        await bot.send_message(
            chat_id,
            "⚠️ Your Telegram is not linked to a MarketWatch account yet.\n\n"
            "Use /link your@email.com to connect.",
        )
        return None
    return profile


# ── Callback query handler ────────────────────────────────────────────────────

async def _handle_callback(bot: Bot, cq: CallbackQuery) -> None:
    chat_id = cq.message.chat.id
    tid = str(chat_id)
    data = cq.data or ""

    await bot.answer_callback_query(cq.id)

    # Main menu
    if data == "menu_main":
        _clear_state(tid)
        await bot.send_message(
            chat_id, "🏠 *Main Menu*\nWhat would you like to do?",
            parse_mode="Markdown", reply_markup=_main_menu_kb(),
        )

    elif data == "menu_alerts":
        _clear_state(tid)
        await bot.send_message(
            chat_id, "🔔 *Alerts*\nManage your price alerts.",
            parse_mode="Markdown", reply_markup=_alerts_menu_kb(),
        )

    elif data == "menu_calc":
        _clear_state(tid)
        await bot.send_message(
            chat_id, "🧮 *Calculator*\nChoose a tool.",
            parse_mode="Markdown", reply_markup=_calc_menu_kb(),
        )

    elif data == "menu_history":
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        history = _get_history(profile["id"])
        if not history:
            await bot.send_message(chat_id, "📭 No triggered alerts yet.", reply_markup=_back_main_kb())
            return
        lines = ["📜 *Recent Triggered Alerts*\n"]
        for a in history:
            emoji = {"touch": "🎯", "cross": "⚡", "near": "📍"}.get(a["alert_type"], "🔔")
            lines.append(f"{emoji} *{a['symbol']}* — {a['alert_type']} @ {a['price']}")
        await bot.send_message(
            chat_id, "\n".join(lines),
            parse_mode="Markdown", reply_markup=_back_main_kb(),
        )

    elif data == "menu_settings":
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        wa = profile.get("whatsapp") or "Not set"
        tier = profile.get("tier", "free")
        await bot.send_message(
            chat_id,
            f"⚙️ *Your Settings*\n\n"
            f"📧 Email: `{profile.get('email', 'N/A')}`\n"
            f"🏅 Plan: *{tier.upper()}*\n"
            f"📱 WhatsApp: `{wa}`\n\n"
            f"To update WhatsApp:\n`/setwhatsapp 2348012345678`",
            parse_mode="Markdown",
            reply_markup=_back_main_kb(),
        )

    elif data == "menu_chat":
        _set_state(tid, "chat_mode")
        await bot.send_message(
            chat_id,
            "💬 *AI Chat Mode*\n\nAsk me any Forex or market question.\nType /menu to return to the main menu.",
            parse_mode="Markdown",
        )

    # ── Alerts
    elif data == "alert_create":
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        tier = profile.get("tier", "free")
        limit = 3 if tier == "free" else 20
        count = _count_active_alerts(profile["id"])
        if count >= limit:
            await bot.send_message(
                chat_id,
                f"⚠️ Alert limit reached ({count}/{limit} for *{tier}* plan).\n"
                "Delete an alert or upgrade to create more.",
                parse_mode="Markdown", reply_markup=_back_alerts_kb(),
            )
            return
        _set_state(tid, "alert_symbol", {"user_id": profile["id"]})
        await bot.send_message(
            chat_id,
            "📝 *Create Alert — Step 1/3*\n\nEnter the trading symbol:\n_(e.g. EURUSD, BTCUSD, XAUUSD)_",
            parse_mode="Markdown",
        )

    elif data == "alert_view":
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        alerts = _get_alerts(profile["id"])
        if not alerts:
            await bot.send_message(chat_id, "📭 No active alerts.", reply_markup=_back_alerts_kb())
            return
        lines = ["📋 *Your Active Alerts*\n"]
        for a in alerts:
            emoji = {"touch": "🎯", "cross": "⚡", "near": "📍"}.get(a["alert_type"], "🔔")
            direction = f" ({a['direction']})" if a.get("direction") else ""
            pip_buf = f" ±{a['pip_buffer']}pip" if a.get("pip_buffer") else ""
            lines.append(f"{emoji} *{a['symbol']}* {a['alert_type']}{direction} @ `{a['price']}`{pip_buf}")
        await bot.send_message(
            chat_id, "\n".join(lines),
            parse_mode="Markdown", reply_markup=_back_alerts_kb(),
        )

    elif data == "alert_delete":
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        alerts = _get_alerts(profile["id"])
        if not alerts:
            await bot.send_message(chat_id, "📭 No active alerts to delete.", reply_markup=_back_alerts_kb())
            return
        buttons = []
        for a in alerts:
            emoji = {"touch": "🎯", "cross": "⚡", "near": "📍"}.get(a["alert_type"], "🔔")
            label = f"🗑 {emoji} {a['symbol']} {a['alert_type']} @ {a['price']}"
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"del_{a['id']}")])
        buttons.append([InlineKeyboardButton(text="◀️ Back", callback_data="menu_alerts")])
        await bot.send_message(
            chat_id, "🗑 *Delete Alert*\n\nTap an alert to delete it:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )

    elif data.startswith("del_"):
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        ok = _delete_alert(data[4:], profile["id"])
        msg = "✅ Alert deleted successfully." if ok else "❌ Could not delete alert."
        await bot.send_message(chat_id, msg, reply_markup=_back_alerts_kb())

    # Alert type selection (step 2 of create flow)
    elif data.startswith("type_"):
        state = _get_state(tid)
        if state["state"] != "alert_type":
            return
        alert_type = data[5:]
        _set_state(tid, "alert_price", {**state["data"], "alert_type": alert_type})
        await bot.send_message(
            chat_id,
            f"✅ Type: *{alert_type}*\n\n💰 *Step 3/3* — Enter the target price:",
            parse_mode="Markdown",
        )

    # Direction selection
    elif data.startswith("dir_"):
        state = _get_state(tid)
        if state["state"] != "alert_direction":
            return
        direction = data[4:]
        d = {**state["data"], "direction": direction}
        ok = _create_alert(d["user_id"], d["symbol"], d["alert_type"], d["price"], d["direction"], None)
        _clear_state(tid)
        if ok:
            await bot.send_message(
                chat_id,
                f"✅ *Alert Created!*\n\n⚡ *{d['symbol']}* cross alert\n"
                f"Triggers when price crosses `{d['price']}` from *{d['direction']}*",
                parse_mode="Markdown", reply_markup=_back_alerts_kb(),
            )
        else:
            await bot.send_message(chat_id, "❌ Failed to create alert.", reply_markup=_back_alerts_kb())

    # Calculator
    elif data == "calc_rr":
        _set_state(tid, "calc_rr_entry")
        await bot.send_message(
            chat_id,
            "⚖️ *Risk/Reward Calculator*\n\n*Step 1/3* — Enter your entry price:",
            parse_mode="Markdown",
        )

    elif data == "calc_ps":
        _set_state(tid, "calc_ps_balance")
        await bot.send_message(
            chat_id,
            "📐 *Position Size Calculator*\n\n*Step 1/4* — Enter your account balance (USD):",
            parse_mode="Markdown",
        )

    elif data == "calc_pip":
        _set_state(tid, "calc_pip_symbol")
        await bot.send_message(
            chat_id,
            "📏 *Pip Calculator*\n\n*Step 1/3* — Enter the symbol (e.g. EURUSD):",
            parse_mode="Markdown",
        )


# ── Text message handler ──────────────────────────────────────────────────────

async def _handle_text(bot: Bot, chat_id: int, text: str) -> None:
    tid = str(chat_id)
    text = text.strip()

    # ── Slash commands
    if text in ("/start", "/menu"):
        _clear_state(tid)
        profile = _get_profile(tid)
        name = profile.get("full_name") or profile.get("email", "Trader") if profile else "Trader"
        greeting = f"Welcome back, {name}!" if profile else "Welcome to MarketWatch AI!"
        await bot.send_message(
            chat_id,
            f"👋 *{greeting}*\n\nChoose an option below:",
            parse_mode="Markdown",
            reply_markup=_main_menu_kb(),
        )
        return

    if text.startswith("/link"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or "@" not in parts[1]:
            await bot.send_message(chat_id, "Usage: /link your@email.com")
            return
        email = parts[1].lower().strip()
        try:
            r = _db().table("profiles").update({"telegram_id": tid}).eq("email", email).execute()
            if r.data:
                await bot.send_message(
                    chat_id,
                    f"✅ *Account Linked!*\n\nYour Telegram is now connected to `{email}`.\nUse /menu to get started.",
                    parse_mode="Markdown",
                )
            else:
                await bot.send_message(chat_id, "❌ No account found with that email. Make sure you've signed up first.")
        except Exception:
            await bot.send_message(chat_id, "⚠️ Something went wrong. Please try again.")
        return

    if text.startswith("/setwhatsapp"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().isdigit():
            await bot.send_message(chat_id, "Usage: /setwhatsapp 2348012345678\n(include country code, no +)")
            return
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        number = parts[1].strip()
        _db().table("profiles").update({"whatsapp": number}).eq("id", profile["id"]).execute()
        await bot.send_message(chat_id, f"✅ WhatsApp number saved: +{number}\nYou'll receive alerts there once the Meta template is approved.")
        return

    if text == "/help":
        await bot.send_message(
            chat_id,
            "🤖 *MarketWatch AI — Commands*\n\n"
            "/menu — Open main menu\n"
            "/link email — Link your MarketWatch account\n"
            "/setwhatsapp number — Save WhatsApp for alerts\n"
            "/clear — Clear AI chat history\n"
            "/help — Show this message",
            parse_mode="Markdown",
        )
        return

    if text == "/clear":
        _chat_history.pop(tid, None)
        _clear_state(tid)
        await bot.send_message(chat_id, "🗑 Chat history cleared.")
        return

    # ── State machine
    state = _get_state(tid)
    s = state["state"]
    d = state["data"]

    # Alert creation steps
    if s == "alert_symbol":
        symbol = text.upper().replace("/", "").replace("-", "").replace(" ", "")
        _set_state(tid, "alert_type", {**d, "symbol": symbol})
        await bot.send_message(
            chat_id,
            f"Symbol: *{symbol}*\n\n*Step 2/3* — Select alert type:",
            parse_mode="Markdown",
            reply_markup=_alert_type_kb(),
        )
        return

    if s == "alert_price":
        try:
            price = float(text)
        except ValueError:
            await bot.send_message(chat_id, "❌ Invalid price. Enter a number (e.g. 1.08500):")
            return
        alert_type = d.get("alert_type")
        if alert_type == "cross":
            _set_state(tid, "alert_direction", {**d, "price": price})
            await bot.send_message(
                chat_id,
                f"Target: `{price}`\n\nWhich direction should price come from?",
                parse_mode="Markdown",
                reply_markup=_direction_kb(),
            )
        elif alert_type == "near":
            _set_state(tid, "alert_pip_buffer", {**d, "price": price})
            await bot.send_message(
                chat_id,
                f"Target: `{price}`\n\nEnter pip buffer — how many pips away to trigger (e.g. 5):",
                parse_mode="Markdown",
            )
        else:
            ok = _create_alert(d["user_id"], d["symbol"], alert_type, price, None, None)
            _clear_state(tid)
            if ok:
                await bot.send_message(
                    chat_id,
                    f"✅ *Alert Created!*\n\n🎯 *{d['symbol']}* touch alert at `{price}`",
                    parse_mode="Markdown", reply_markup=_back_alerts_kb(),
                )
            else:
                await bot.send_message(chat_id, "❌ Failed to create alert.", reply_markup=_back_alerts_kb())
        return

    if s == "alert_pip_buffer":
        try:
            pip_buffer = float(text)
        except ValueError:
            await bot.send_message(chat_id, "❌ Enter a valid number (e.g. 5):")
            return
        ok = _create_alert(d["user_id"], d["symbol"], d["alert_type"], d["price"], None, pip_buffer)
        _clear_state(tid)
        if ok:
            await bot.send_message(
                chat_id,
                f"✅ *Alert Created!*\n\n📍 *{d['symbol']}* near alert at `{d['price']}` ±{pip_buffer} pips",
                parse_mode="Markdown", reply_markup=_back_alerts_kb(),
            )
        else:
            await bot.send_message(chat_id, "❌ Failed to create alert.", reply_markup=_back_alerts_kb())
        return

    # Risk/Reward calculator
    if s == "calc_rr_entry":
        try:
            _set_state(tid, "calc_rr_sl", {**d, "entry": float(text)})
            await bot.send_message(chat_id, "*Step 2/3* — Enter your stop loss price:", parse_mode="Markdown")
        except ValueError:
            await bot.send_message(chat_id, "❌ Enter a valid price:")
        return

    if s == "calc_rr_sl":
        try:
            _set_state(tid, "calc_rr_tp", {**d, "sl": float(text)})
            await bot.send_message(chat_id, "*Step 3/3* — Enter your take profit price:", parse_mode="Markdown")
        except ValueError:
            await bot.send_message(chat_id, "❌ Enter a valid price:")
        return

    if s == "calc_rr_tp":
        try:
            tp = float(text)
            entry, sl = d["entry"], d["sl"]
            risk = abs(entry - sl)
            reward = abs(tp - entry)
            ratio = round(reward / risk, 2) if risk > 0 else 0
            pip = 0.0001
            _clear_state(tid)
            await bot.send_message(
                chat_id,
                f"⚖️ *Risk/Reward Result*\n\n"
                f"Entry: `{entry}`  |  SL: `{sl}`  |  TP: `{tp}`\n\n"
                f"Risk: *{round(risk/pip,1)} pips*\n"
                f"Reward: *{round(reward/pip,1)} pips*\n"
                f"Ratio: *1:{ratio}*",
                parse_mode="Markdown", reply_markup=_back_calc_kb(),
            )
        except ValueError:
            await bot.send_message(chat_id, "❌ Enter a valid price:")
        return

    # Position size
    if s == "calc_ps_balance":
        try:
            _set_state(tid, "calc_ps_risk", {**d, "balance": float(text)})
            await bot.send_message(chat_id, "*Step 2/4* — Enter your risk % per trade (e.g. 1 or 2):", parse_mode="Markdown")
        except ValueError:
            await bot.send_message(chat_id, "❌ Enter a valid number:")
        return

    if s == "calc_ps_risk":
        try:
            _set_state(tid, "calc_ps_sl_pips", {**d, "risk_pct": float(text)})
            await bot.send_message(chat_id, "*Step 3/4* — Enter stop loss in pips:", parse_mode="Markdown")
        except ValueError:
            await bot.send_message(chat_id, "❌ Enter a valid number:")
        return

    if s == "calc_ps_sl_pips":
        try:
            _set_state(tid, "calc_ps_pip_val", {**d, "sl_pips": float(text)})
            await bot.send_message(chat_id, "*Step 4/4* — Enter pip value per standard lot (e.g. 10 for EURUSD):", parse_mode="Markdown")
        except ValueError:
            await bot.send_message(chat_id, "❌ Enter a valid number:")
        return

    if s == "calc_ps_pip_val":
        try:
            pip_val = float(text)
            risk_amt = round(d["balance"] * (d["risk_pct"] / 100), 2)
            lots = round(risk_amt / (d["sl_pips"] * pip_val), 4) if d["sl_pips"] * pip_val > 0 else 0
            units = int(lots * 100_000)
            _clear_state(tid)
            await bot.send_message(
                chat_id,
                f"📐 *Position Size Result*\n\n"
                f"Balance: *${d['balance']:,.2f}*  |  Risk: *{d['risk_pct']}%*\n"
                f"Stop Loss: *{d['sl_pips']} pips*\n\n"
                f"Lot Size: *{lots}*\n"
                f"Units: *{units:,}*\n"
                f"Risk Amount: *${risk_amt:,.2f}*",
                parse_mode="Markdown", reply_markup=_back_calc_kb(),
            )
        except ValueError:
            await bot.send_message(chat_id, "❌ Enter a valid number:")
        return

    # Pip calculator
    if s == "calc_pip_symbol":
        _set_state(tid, "calc_pip_p1", {**d, "symbol": text.upper()})
        await bot.send_message(chat_id, f"Symbol: *{text.upper()}*\n\n*Step 2/3* — Enter price from:", parse_mode="Markdown")
        return

    if s == "calc_pip_p1":
        try:
            _set_state(tid, "calc_pip_p2", {**d, "p1": float(text)})
            await bot.send_message(chat_id, "*Step 3/3* — Enter price to:", parse_mode="Markdown")
        except ValueError:
            await bot.send_message(chat_id, "❌ Enter a valid price:")
        return

    if s == "calc_pip_p2":
        try:
            p2 = float(text)
            p1 = d["p1"]
            symbol = d["symbol"]
            diff = p2 - p1
            pips = round(abs(diff) / _pip_size(symbol), 1)
            direction = "up 📈" if diff > 0 else "down 📉"
            _clear_state(tid)
            await bot.send_message(
                chat_id,
                f"📏 *Pip Calculator Result*\n\n"
                f"Symbol: *{symbol}*\n"
                f"`{p1}` → `{p2}`\n\n"
                f"Movement: *{pips} pips {direction}*",
                parse_mode="Markdown", reply_markup=_back_calc_kb(),
            )
        except ValueError:
            await bot.send_message(chat_id, "❌ Enter a valid price:")
        return

    # AI chat (chat_mode state or default fallback)
    profile = _get_profile(tid)
    tier = profile.get("tier", "free") if profile else "free"
    history = _chat_history.get(tid, [])
    user_msgs = [m for m in history if m["role"] == "user"]

    if tier == "free" and len(user_msgs) >= FREE_CHAT_LIMIT:
        await bot.send_message(
            chat_id,
            f"⚠️ You've used your {FREE_CHAT_LIMIT} free AI questions this session.\n\n"
            "Upgrade to *PRO* for unlimited AI chat! Visit the website to upgrade.",
            parse_mode="Markdown",
            reply_markup=_back_main_kb(),
        )
        return

    history.append({"role": "user", "content": text})
    _chat_history[tid] = history
    await bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        reply = await asyncio.to_thread(ai_chat, history)
        history.append({"role": "assistant", "content": reply})
        _chat_history[tid] = history[-20:]
        await bot.send_message(chat_id, reply)
    except Exception as exc:
        logger.error("AI chat error: %s", exc)
        await bot.send_message(chat_id, "⚠️ AI is temporarily unavailable. Please try again shortly.")


# ── Webhook endpoint ──────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict[str, Any]:
    body = await request.json()
    bot = get_bot()
    update = Update.model_validate(body)

    if update.callback_query:
        await _handle_callback(bot, update.callback_query)
    elif update.message and update.message.text:
        await _handle_text(bot, update.message.chat.id, update.message.text)

    await _dp.feed_update(bot=bot, update=update)
    return {"ok": True}
