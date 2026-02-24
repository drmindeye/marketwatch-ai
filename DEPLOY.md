# MarketWatch AI — Railway Deployment Guide

## 1. Prerequisites

- Railway account → https://railway.app
- Supabase project created
- Paystack account (live keys)
- Meta Developer App (WhatsApp Business)
- Telegram Bot created via @BotFather
- FMP API key (Financial Modeling Prep)
- Anthropic API key

---

## 2. Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link project
railway login
railway init

# Deploy both services
railway up
```

Railway will detect `railway.toml` and deploy `backend` and `frontend` as separate services.

---

## 3. Environment Variables

### Backend service (set in Railway dashboard → backend → Variables)

| Variable                  | Value                                      |
|---------------------------|--------------------------------------------|
| `SUPABASE_URL`            | From Supabase → Project Settings → API     |
| `SUPABASE_SERVICE_KEY`    | From Supabase → Project Settings → API     |
| `FMP_API_KEY`             | From financialmodelingprep.com             |
| `PAYSTACK_SECRET_KEY`     | From Paystack → Settings → API Keys (Live) |
| `ANTHROPIC_API_KEY`       | From console.anthropic.com                 |
| `WHATSAPP_ACCESS_TOKEN`   | From Meta Developer → WhatsApp → API Setup |
| `WHATSAPP_PHONE_NUMBER_ID`| From Meta Developer → WhatsApp → API Setup |
| `WHATSAPP_VERIFY_TOKEN`   | Any secret string you choose               |
| `TELEGRAM_BOT_TOKEN`      | From @BotFather on Telegram                |
| `FRONTEND_URL`            | Your Railway frontend URL (after deploy)   |

### Frontend service (set in Railway dashboard → frontend → Variables)

| Variable                       | Value                                  |
|--------------------------------|----------------------------------------|
| `NEXT_PUBLIC_SUPABASE_URL`     | From Supabase → Project Settings → API |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`| From Supabase → Project Settings → API |
| `PAYSTACK_SECRET_KEY`          | Same as backend (for /api/checkout)    |

> Build-time variables (`NEXT_PUBLIC_*`) must also be set as Railway **Build Variables**.

---

## 4. Supabase Setup

1. Go to your Supabase project → **SQL Editor**
2. Paste and run the full contents of `supabase/migrations/001_initial_schema.sql`
3. Go to **Authentication → URL Configuration**:
   - Site URL: `https://your-frontend.up.railway.app`
   - Redirect URL: `https://your-frontend.up.railway.app/auth/callback`

---

## 5. Webhook URLs (set after Railway deploy)

### Paystack
- Dashboard → Settings → Webhooks
- URL: `https://your-backend.up.railway.app/api/payments/webhook`
- Events to enable: `charge.success`

### Meta (WhatsApp Cloud API)
- Meta Developer → your App → WhatsApp → Configuration → Webhooks
- Callback URL: `https://your-backend.up.railway.app/api/whatsapp/webhook`
- Verify Token: must match `WHATSAPP_VERIFY_TOKEN` env var
- Subscribe to: `messages`

### Telegram Bot
Run once after deploy (replace values):
```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-backend.up.railway.app/api/telegram/webhook"}'
```

---

## 6. WhatsApp Message Template

In Meta Business Manager → WhatsApp Manager → Message Templates, create:

- **Template name:** `market_alert`
- **Category:** Utility
- **Language:** English (US)
- **Body:**
  ```
  🔔 *{{1}} Alert Triggered*
  Type: {{2}}
  Current Price: {{3}}
  Your Level: {{4}}

  AI Summary: {{5}}
  ```

Wait for Meta approval (usually 24–48 hours).

---

## 7. Verify Deployment

```bash
# Health check
curl https://your-backend.up.railway.app/health
# Expected: {"status": "ok"}

# Trade calculator smoke test
curl -X POST https://your-backend.up.railway.app/api/trade/pips \
  -H "Content-Type: application/json" \
  -d '{"symbol": "EURUSD", "price_from": 1.1000, "price_to": 1.1050}'
# Expected: {"pips": 50.0, "direction": "up"}
```
