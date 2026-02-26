"""Telegram bot — full menu interface with alerts, calculator, history, settings."""

import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Any

import httpx
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
from services.ai import chat as ai_chat, parse_reminder, detect_symbol
from services.fmp import fetch_batch_quotes

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
    zone_high: float | None = None,
) -> bool:
    try:
        _db().table("alerts").insert({
            "user_id": user_id,
            "symbol": symbol.upper(),
            "alert_type": alert_type,
            "price": price,
            "direction": direction,
            "pip_buffer": pip_buffer if pip_buffer is not None else 5.0,
            "zone_high": zone_high,
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


def _count_today_alerts(user_id: str) -> int:
    try:
        today_start = date.today().isoformat() + "T00:00:00+00:00"
        r = (
            _db().table("alerts")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", today_start)
            .execute()
        )
        return r.count or 0
    except Exception:
        return 0


def _get_active_alert_symbols(user_id: str) -> set[str]:
    try:
        r = (
            _db().table("alerts")
            .select("symbol")
            .eq("user_id", user_id)
            .is_("triggered_at", "null")
            .execute()
        )
        return {row["symbol"] for row in (r.data or [])}
    except Exception:
        return set()


def _get_reminders(user_id: str) -> list[dict]:
    try:
        r = (
            _db().table("reminders")
            .select("*")
            .eq("user_id", user_id)
            .eq("sent", False)
            .order("remind_at", desc=False)
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def _create_reminder(user_id: str, message: str, remind_at: str, session_type: str | None, is_recurring: bool) -> bool:
    try:
        _db().table("reminders").insert({
            "user_id": user_id,
            "message": message,
            "remind_at": remind_at,
            "session_type": session_type,
            "is_recurring": is_recurring,
            "sent": False,
        }).execute()
        return True
    except Exception as e:
        logger.error("Create reminder error: %s", e)
        return False


def _delete_reminder(reminder_id: str, user_id: str) -> bool:
    try:
        _db().table("reminders").delete().eq("id", reminder_id).eq("user_id", user_id).execute()
        return True
    except Exception:
        return False


def _get_platform_stats() -> dict:
    try:
        db = _db()
        total = db.table("profiles").select("id", count="exact").execute().count or 0
        paid = db.table("profiles").select("id", count="exact").in_("tier", ["pro", "elite"]).execute().count or 0
        free = db.table("profiles").select("id", count="exact").eq("tier", "free").execute().count or 0
        expired = db.table("subscriptions").select("id", count="exact").eq("status", "expired").execute().count or 0
        cancelled = db.table("subscriptions").select("id", count="exact").eq("status", "cancelled").execute().count or 0
        return {"total": total, "paid": paid, "free": free, "expired": expired, "cancelled": cancelled}
    except Exception as e:
        logger.error("Stats error: %s", e)
        return {}


# ── Keyboards ─────────────────────────────────────────────────────────────────

def _main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔔 Alerts", callback_data="menu_alerts"),
            InlineKeyboardButton(text="⏰ Reminders", callback_data="menu_reminders"),
        ],
        [
            InlineKeyboardButton(text="🧮 Calculator", callback_data="menu_calc"),
            InlineKeyboardButton(text="📊 Correlations", callback_data="menu_correlation"),
        ],
        [
            InlineKeyboardButton(text="📜 History", callback_data="menu_history"),
            InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings"),
        ],
        [InlineKeyboardButton(text="💬 AI Chat", callback_data="menu_chat")],
        [InlineKeyboardButton(text="💎 Upgrade to Pro", callback_data="menu_upgrade")],
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
        ],
        [
            InlineKeyboardButton(text="📍 Near", callback_data="type_near"),
            InlineKeyboardButton(text="📦 Zone", callback_data="type_zone"),
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


def _reminders_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Set Reminder", callback_data="reminder_create")],
        [InlineKeyboardButton(text="📋 My Reminders", callback_data="reminder_list")],
        [InlineKeyboardButton(text="🗑 Delete Reminder", callback_data="reminder_delete")],
        [InlineKeyboardButton(text="◀️ Main Menu", callback_data="menu_main")],
    ])


def _session_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌏 Asian Session (00:00 UTC)", callback_data="session_asian")],
        [InlineKeyboardButton(text="🇬🇧 London Session (08:00 UTC)", callback_data="session_london")],
        [InlineKeyboardButton(text="🇺🇸 New York Session (13:00 UTC)", callback_data="session_new_york")],
        [InlineKeyboardButton(text="✏️ Custom Time / AI Parse", callback_data="session_custom")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="menu_reminders")],
    ])


def _back_reminders_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Reminders", callback_data="menu_reminders")],
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

    elif data == "menu_upgrade":
        await bot.send_message(
            chat_id,
            "💎 *Upgrade to MarketWatch AI Pro*\n\n"
            "*🔓 What you get:*\n"
            "• Unlimited price alerts\n"
            "• Unlimited trading pairs\n"
            "• WhatsApp alert notifications\n"
            "• Zone & correlation alerts\n"
            "• Unlimited AI chat\n\n"
            "*💰 Pricing:*\n"
            "• Weekly: ₦2,000\n"
            "• Monthly: ₦7,000\n\n"
            f"👉 [Upgrade now]({settings.FRONTEND_URL}/dashboard)",
            parse_mode="Markdown",
            reply_markup=_back_main_kb(),
        )

    # ── Reminders menu
    elif data == "menu_reminders":
        _clear_state(tid)
        await bot.send_message(
            chat_id, "⏰ *Reminders*\nNever miss a session open or event.",
            parse_mode="Markdown", reply_markup=_reminders_menu_kb(),
        )

    elif data == "reminder_create":
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        _set_state(tid, "reminder_type", {"user_id": profile["id"]})
        await bot.send_message(
            chat_id,
            "⏰ *New Reminder*\n\nChoose a type:",
            parse_mode="Markdown", reply_markup=_session_kb(),
        )

    elif data.startswith("session_"):
        state = _get_state(tid)
        if state["state"] != "reminder_type":
            return
        session = data[8:]  # asian / london / new_york / custom
        user_id = state["data"]["user_id"]

        if session == "custom":
            _set_state(tid, "reminder_custom", {"user_id": user_id})
            await bot.send_message(
                chat_id,
                "✏️ *Custom Reminder*\n\nTell me what to remind you and when.\n\n"
                "_Examples:_\n"
                "• `Remind me at 2am to attend the summit on X`\n"
                "• `Remind me tomorrow at 9pm to review my trades`\n"
                "• `Remind me every day at the London session to check EURUSD`",
                parse_mode="Markdown",
            )
            return

        # Session reminder
        from services.reminder_worker import SESSION_TIMES
        from datetime import timedelta
        h, m = SESSION_TIMES[session]
        now_utc = datetime.now(timezone.utc)
        next_dt = now_utc.replace(hour=h, minute=m, second=0, microsecond=0)
        if next_dt <= now_utc:
            next_dt += timedelta(days=1)

        labels = {"asian": "Asian 🌏", "london": "London 🇬🇧", "new_york": "New York 🇺🇸"}
        msg = f"{labels[session]} session open — time to trade!"
        ok = _create_reminder(user_id, msg, next_dt.isoformat(), session, is_recurring=True)
        _clear_state(tid)
        if ok:
            await bot.send_message(
                chat_id,
                f"✅ *Reminder Set!*\n\n{labels[session]} session reminder created.\n"
                f"I'll ping you daily at *{h:02d}:{m:02d} UTC*.",
                parse_mode="Markdown", reply_markup=_back_reminders_kb(),
            )
        else:
            await bot.send_message(chat_id, "❌ Could not set reminder.", reply_markup=_back_reminders_kb())

    elif data == "reminder_list":
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        reminders = _get_reminders(profile["id"])
        if not reminders:
            await bot.send_message(chat_id, "📭 No active reminders.", reply_markup=_back_reminders_kb())
            return
        lines = ["📋 *Your Reminders*\n"]
        for r in reminders:
            dt = r["remind_at"][:16].replace("T", " ") + " UTC"
            recurring = " (daily 🔁)" if r["is_recurring"] else ""
            lines.append(f"⏰ {r['message'][:50]}\n   📅 {dt}{recurring}")
        await bot.send_message(
            chat_id, "\n\n".join(lines),
            parse_mode="Markdown", reply_markup=_back_reminders_kb(),
        )

    elif data == "reminder_delete":
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        reminders = _get_reminders(profile["id"])
        if not reminders:
            await bot.send_message(chat_id, "📭 No reminders to delete.", reply_markup=_back_reminders_kb())
            return
        buttons = []
        for r in reminders:
            label = f"🗑 {r['message'][:40]}"
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"delrem_{r['id']}")])
        buttons.append([InlineKeyboardButton(text="◀️ Back", callback_data="menu_reminders")])
        await bot.send_message(
            chat_id, "🗑 *Delete Reminder*\n\nTap one to delete:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )

    elif data.startswith("delrem_"):
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        ok = _delete_reminder(data[7:], profile["id"])
        msg = "✅ Reminder deleted." if ok else "❌ Could not delete reminder."
        await bot.send_message(chat_id, msg, reply_markup=_back_reminders_kb())

    # ── Correlation
    elif data == "menu_correlation":
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        try:
            import httpx
            groups = {
                "Dollar Pairs 💵": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF"],
                "Safe Haven 🛡": ["XAUUSD", "USDJPY", "USDCHF", "BTCUSD"],
                "Risk-On 📈": ["GBPJPY", "AUDUSD", "BTCUSD", "ETHUSD"],
            }
            all_symbols = list({s for g in groups.values() for s in g})
            backend = settings.FRONTEND_URL.replace("feisty-happiness", "sweet-smile").replace("52e2", "e1c5")
            # Use internal FMP fetch instead
            from services.fmp import fetch_batch_quotes
            quotes = await fetch_batch_quotes(all_symbols)

            tier = profile.get("tier", "free")
            group_items = list(groups.items())
            if tier == "free":
                group_items = group_items[:1]  # free: 1 group only

            lines = ["📊 *Market Correlations*\n"]
            for group_name, symbols in group_items:
                lines.append(f"*{group_name}*")
                for sym in symbols:
                    q = quotes.get(sym)
                    if q:
                        chg = q.get("changesPercentage", 0)
                        arrow = "📈" if chg >= 0 else "📉"
                        lines.append(f"  {arrow} `{sym}` {q['price']:.5f} ({chg:+.2f}%)")
                    else:
                        lines.append(f"  • `{sym}` — N/A")
                lines.append("")

            if tier == "free":
                lines.append("🔒 _Pro unlocks Safe Haven + Risk-On groups_\n/upgrade")

            await bot.send_message(
                chat_id, "\n".join(lines),
                parse_mode="Markdown", reply_markup=_back_main_kb(),
            )
        except Exception as exc:
            logger.error("Correlation fetch error: %s", exc)
            await bot.send_message(chat_id, "⚠️ Could not fetch prices. Try again.", reply_markup=_back_main_kb())

    # ── Alerts
    elif data == "alert_create":
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        tier = profile.get("tier", "free")
        if tier == "free":
            daily = _count_today_alerts(profile["id"])
            if daily >= 2:
                await bot.send_message(
                    chat_id,
                    "⚠️ *Daily limit reached!*\n\n"
                    "Free plan allows *2 alerts per day*.\n\n"
                    "💎 Upgrade to Pro for unlimited alerts!\n/upgrade",
                    parse_mode="Markdown", reply_markup=_back_alerts_kb(),
                )
                return
        _set_state(tid, "alert_symbol", {"user_id": profile["id"], "tier": tier})
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
        if alert_type == "zone" and state["data"].get("tier", "free") == "free":
            await bot.send_message(
                chat_id,
                "🔒 *Zone alerts are a Pro feature.*\n\n"
                "Upgrade to unlock Zone & correlation alerts.\n/upgrade",
                parse_mode="Markdown", reply_markup=_back_alerts_kb(),
            )
            _clear_state(tid)
            return
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

async def _handle_text(bot: Bot, chat_id: int, text: str, first_name: str | None = None) -> None:
    tid = str(chat_id)
    text = text.strip()

    # ── Slash commands
    if text == "/start":
        _clear_state(tid)
        profile = _get_profile(tid)
        linked_line = (
            f"✅ Linked to: `{profile.get('email', '')}`  |  Plan: *{profile.get('tier', 'free').upper()}*"
            if profile
            else "⚠️ Not linked yet — use /link your@email.com to connect."
        )
        await bot.send_message(
            chat_id,
            f"🤖 *Welcome to MarketWatch AI Bot!*\n\n"
            f"Your Telegram ID: `{tid}`\n"
            f"{linked_line}\n\n"
            "*📊 Features:*\n"
            "🔔 Price Alerts — Touch, Cross, Near & Zone\n"
            "⏰ Reminders — Session opens + custom reminders\n"
            "📊 Correlations — Live pair correlation groups\n"
            "🧮 Trade Calculator — Risk/Reward, Position Size, Pips\n"
            "📜 Alert History — All triggered alerts\n"
            "💬 AI Chat — Powered by DeepSeek AI\n"
            "⚙️ Account Settings — Manage your profile\n\n"
            "*📦 Plans:*\n"
            "🆓 *Free* — 1 pair, 2 alerts/day, Telegram only\n"
            "💎 *Pro* — Unlimited alerts & pairs, WhatsApp, Zone alerts\n\n"
            "*Commands:*\n"
            "/menu — Open main menu\n"
            "/remind — Set a reminder\n"
            "/upgrade — View Pro plans & pricing\n"
            "/link email — Connect your account\n"
            "/id — Show your Telegram ID\n"
            "/support — Contact support\n"
            "/help — All commands",
            parse_mode="Markdown",
        )
        return

    if text == "/menu":
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

    if text == "/upgrade":
        await bot.send_message(
            chat_id,
            "💎 *Upgrade to MarketWatch AI Pro*\n\n"
            "*🔓 What you get:*\n"
            "• Unlimited price alerts\n"
            "• Unlimited trading pairs\n"
            "• WhatsApp alert notifications\n"
            "• Zone & correlation alerts\n"
            "• Unlimited AI chat\n\n"
            "*💰 Pricing:*\n"
            "• Weekly: ₦2,000\n"
            "• Monthly: ₦7,000\n\n"
            f"👉 [Upgrade now]({settings.FRONTEND_URL}/dashboard)",
            parse_mode="Markdown",
        )
        return

    if text == "/id":
        await bot.send_message(
            chat_id,
            f"🪪 Your Telegram ID: `{tid}`",
            parse_mode="Markdown",
        )
        return

    if text == "/support":
        await bot.send_message(
            chat_id,
            "🆘 *Need help?*\n\n"
            "Contact our support team directly on Telegram:\n"
            "👤 @MarketWatchSupport\n\n"
            "We typically respond within a few hours.",
            parse_mode="Markdown",
        )
        return

    if text == "/stats":
        profile = _get_profile(tid)
        if not profile or not profile.get("is_admin"):
            await bot.send_message(chat_id, "⛔ This command is for admins only.")
            return
        stats = _get_platform_stats()
        if not stats:
            await bot.send_message(chat_id, "⚠️ Could not fetch stats. Try again.")
            return
        await bot.send_message(
            chat_id,
            "📊 *MarketWatch AI — Platform Stats*\n\n"
            f"👥 Total Users: *{stats.get('total', 0)}*\n"
            f"💎 Pro/Elite Users: *{stats.get('paid', 0)}*\n"
            f"🆓 Free Users: *{stats.get('free', 0)}*\n"
            f"📋 Expired Subscriptions: *{stats.get('expired', 0)}*\n"
            f"❌ Cancelled Subscriptions: *{stats.get('cancelled', 0)}*",
            parse_mode="Markdown",
        )
        return

    if text.startswith("/link"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or "@" not in parts[1]:
            await bot.send_message(chat_id, "Usage: /link your@email.com")
            return
        email = parts[1].lower().strip()
        try:
            db = _db()
            # Try updating existing profile first
            r = db.table("profiles").update({"telegram_id": tid}).eq("email", email).execute()
            if r.data:
                await bot.send_message(
                    chat_id,
                    f"✅ *Account Linked!*\n\nYour Telegram is now connected to `{email}`.\nUse /menu to get started.",
                    parse_mode="Markdown",
                )
                return

            # Profile row missing — look up auth user via REST API and create profile
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{settings.SUPABASE_URL}/auth/v1/admin/users",
                    headers={
                        "apikey": settings.SUPABASE_SERVICE_KEY,
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    },
                    params={"per_page": 1000, "page": 1},
                )

            if resp.status_code != 200:
                logger.error("Auth admin API error: %s", resp.text)
                await bot.send_message(chat_id, "⚠️ Something went wrong. Please try again.")
                return

            users = resp.json().get("users", [])
            auth_user = next(
                (u for u in users if u.get("email", "").lower() == email),
                None,
            )
            if not auth_user:
                await bot.send_message(
                    chat_id,
                    "❌ No account found with that email.\n\nMake sure you signed up at the MarketWatch AI website first.",
                )
                return

            # Create the missing profile row and link Telegram in one upsert
            db.table("profiles").upsert({
                "id": auth_user["id"],
                "email": email,
                "tier": "free",
                "telegram_id": tid,
            }).execute()
            await bot.send_message(
                chat_id,
                f"✅ *Account Linked!*\n\nYour Telegram is now connected to `{email}`.\nUse /menu to get started.",
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.error("Link account error: %s", exc)
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
            "/start — Welcome message & features\n"
            "/menu — Open main menu\n"
            "/remind — Set a session or custom reminder\n"
            "/upgrade — View Pro plans & pricing\n"
            "/id — Show your Telegram ID\n"
            "/support — Contact support\n"
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

    if text.startswith("/promote"):
        profile = _get_profile(tid)
        if not profile or not profile.get("is_admin"):
            await bot.send_message(chat_id, "⛔ Admin only.")
            return
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await bot.send_message(chat_id, "Usage: /promote user@email.com")
            return
        identifier = parts[1].strip()
        try:
            db = _db()
            # Find by email or id
            r = db.table("profiles").select("id,email,tier").eq("email", identifier).maybe_single().execute()
            if not r.data:
                r = db.table("profiles").select("id,email,tier").eq("id", identifier).maybe_single().execute()
            if not r.data:
                await bot.send_message(chat_id, f"❌ No user found: {identifier}")
                return
            target = r.data
            if target["tier"] == "pro":
                await bot.send_message(chat_id, f"ℹ️ {target['email']} is already Pro.")
                return
            db.table("profiles").update({"tier": "pro"}).eq("id", target["id"]).execute()
            db.table("subscriptions").insert({
                "user_id": target["id"],
                "paystack_ref": f"admin_grant_{target['id'][:8]}",
                "plan": "pro",
                "status": "active",
                "amount": 0,
                "currency": "NGN",
            }).execute()
            await bot.send_message(
                chat_id,
                f"✅ *{target['email']}* promoted to *Pro*.",
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.error("Promote error: %s", exc)
            await bot.send_message(chat_id, "⚠️ Promote failed. Check logs.")
        return

    if text.startswith("/remind"):
        profile = await _require_linked(bot, chat_id, tid)
        if not profile:
            return
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            _set_state(tid, "reminder_type", {"user_id": profile["id"]})
            await bot.send_message(
                chat_id, "⏰ *Set a Reminder*\nChoose type:",
                parse_mode="Markdown", reply_markup=_session_kb(),
            )
        else:
            # Inline: /remind <natural language>
            reminder_text = parts[1]
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            now_utc = datetime.now(timezone.utc).isoformat()
            parsed = await asyncio.to_thread(parse_reminder, reminder_text, now_utc)
            if not parsed or not parsed.get("remind_at"):
                await bot.send_message(
                    chat_id,
                    "❌ Couldn't parse that reminder. Try:\n`/remind me at 9pm to review my trades`",
                    parse_mode="Markdown",
                )
                return
            ok = _create_reminder(
                profile["id"],
                parsed.get("message", reminder_text),
                parsed["remind_at"],
                parsed.get("session_type"),
                parsed.get("is_recurring", False),
            )
            if ok:
                dt = parsed["remind_at"][:16].replace("T", " ")
                await bot.send_message(
                    chat_id,
                    f"✅ *Reminder Set!*\n\n_{parsed.get('message', reminder_text)}_\n📅 {dt} UTC",
                    parse_mode="Markdown", reply_markup=_back_main_kb(),
                )
            else:
                await bot.send_message(chat_id, "❌ Failed to save reminder.")
        return

    # ── State machine
    state = _get_state(tid)
    s = state["state"]
    d = state["data"]

    # Custom reminder via AI parsing
    if s == "reminder_custom":
        user_id = d["user_id"]
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        now_utc = datetime.now(timezone.utc).isoformat()
        parsed = await asyncio.to_thread(parse_reminder, text, now_utc)
        if not parsed or not parsed.get("remind_at"):
            await bot.send_message(
                chat_id,
                "❌ Couldn't understand that. Try:\n`Remind me at 9pm to review my EURUSD trade`",
                parse_mode="Markdown",
            )
            return
        ok = _create_reminder(
            user_id,
            parsed.get("message", text),
            parsed["remind_at"],
            parsed.get("session_type"),
            parsed.get("is_recurring", False),
        )
        _clear_state(tid)
        if ok:
            dt = parsed["remind_at"][:16].replace("T", " ")
            recurring = " (recurring daily)" if parsed.get("is_recurring") else ""
            await bot.send_message(
                chat_id,
                f"✅ *Reminder Set!*\n\n_{parsed.get('message', text)}_\n📅 {dt} UTC{recurring}",
                parse_mode="Markdown", reply_markup=_back_reminders_kb(),
            )
        else:
            await bot.send_message(chat_id, "❌ Failed to save reminder.", reply_markup=_back_reminders_kb())
        return

    # Alert creation steps
    if s == "alert_symbol":
        symbol = text.upper().replace("/", "").replace("-", "").replace(" ", "")
        if d.get("tier", "free") == "free":
            existing_symbols = _get_active_alert_symbols(d["user_id"])
            if existing_symbols and symbol not in existing_symbols:
                current = next(iter(existing_symbols))
                await bot.send_message(
                    chat_id,
                    f"⚠️ *Pair limit reached!*\n\n"
                    f"Free plan allows *1 trading pair* (currently: *{current}*).\n\n"
                    "Delete your existing alerts first, or upgrade to Pro for unlimited pairs.\n/upgrade",
                    parse_mode="Markdown", reply_markup=_back_alerts_kb(),
                )
                _clear_state(tid)
                return
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
        elif alert_type == "zone":
            _set_state(tid, "alert_zone_high", {**d, "price": price})
            await bot.send_message(
                chat_id,
                f"Zone Low: `{price}`\n\nNow enter the *zone high* (upper bound):",
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

    if s == "alert_zone_high":
        try:
            zone_high = float(text)
        except ValueError:
            await bot.send_message(chat_id, "❌ Invalid price. Enter a number (e.g. 1.08500):")
            return
        if zone_high <= d["price"]:
            await bot.send_message(chat_id, f"❌ Zone high must be above zone low ({d['price']}):")
            return
        ok = _create_alert(d["user_id"], d["symbol"], "zone", d["price"], None, None, zone_high)
        _clear_state(tid)
        if ok:
            await bot.send_message(
                chat_id,
                f"✅ *Alert Created!*\n\n📦 *{d['symbol']}* zone alert\n"
                f"Triggers when price enters `{d['price']}` – `{zone_high}`",
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

    # Detect symbol → fetch live price → inject as context so AI gives relevant zones
    price_context: str | None = None
    symbol = detect_symbol(text)
    if symbol:
        try:
            quotes = await fetch_batch_quotes([symbol])
            q = quotes.get(symbol)
            if q:
                price = q.get("price", 0)
                chg = q.get("changesPercentage", 0)
                price_context = (
                    f"{symbol} live price: {price} ({chg:+.2f}% today)\n"
                    f"Base ALL zones and levels on this exact current price."
                )
        except Exception as exc:
            logger.warning("Price fetch for AI context failed (%s): %s", symbol, exc)

    try:
        reply = await asyncio.to_thread(ai_chat, history, price_context)
        history.append({"role": "assistant", "content": reply})
        _chat_history[tid] = history[-20:]
        await bot.send_message(chat_id, reply, parse_mode="Markdown")
    except Exception as exc:
        logger.error("AI chat error: %s", exc)
        # Retry without Markdown parse mode in case of formatting issues
        try:
            await bot.send_message(chat_id, reply)
        except Exception:
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
        from_user = update.message.from_user
        first_name = from_user.first_name if from_user else None
        await _handle_text(bot, update.message.chat.id, update.message.text, first_name)

    await _dp.feed_update(bot=bot, update=update)
    return {"ok": True}
