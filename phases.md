# Production Roadmap: MarketWatch AI

## Phase 1: Infrastructure & Authentication
- **Objective:** Setup folders and secure user access.
- **Task 1.1:** Initialize `/frontend` (Next.js) and `/backend` (FastAPI).
- **Task 1.2:** Configure Supabase tables: `profiles`, `alerts`, `subscriptions`, `market_news`.
- **Task 1.3:** Build Landing Page: Header, Hero, Features, Pricing (Free/Pro/Elite), Footer.
- **Task 1.4:** Implement Auth Flow: Signup, Login, Callback, Proxy, and Server-side Logout.

## Phase 2: Paystack Payment System & Security
- **Objective:** Monetize the bot and secure the transaction loop.
- **Task 2.1:** Build `backend/api/payments.py` with HMAC SHA512 verification.
- **Task 2.2:** Handle `charge.success`: Update Supabase `profiles` set `tier='pro'`.
- **Task 2.3:** Link Pricing CTA in Next.js to Paystack Checkout.

## Phase 3: FMP Engine & AI Logic
- **Objective:** Build the market monitoring "Brain".
- **Task 3.1:** Create Python background worker using FMP Batch Quote API.
- **Task 3.2:** Implement Alert Trigger Logic: Touch, Cross, and Near Level (Pip buffer).
- **Task 3.3:** Build Trade Assistant: Risk/Reward, Position Sizing, and Pips calculator.
- **Task 3.4:** Integrate Claude 3.5 Sonnet for Forex market summaries and AI chat.

## Phase 4: WhatsApp (Direct) & Telegram Notification Hub
- **Objective:** Deliver alerts with zero delay.
- **Task 4.1:** Build `whatsapp_service.py` calling Meta Graph API directly (Templates).
- **Task 4.2:** Build Telegram Bot using `aiogram`.
- **Task 4.3:** Create Dispatcher: If PRO, send to WhatsApp + Telegram. If FREE, Telegram only.
- **Task 4.4:** Build Admin Dashboard to track user tiers and total revenue.

## Phase 5: Deployment
- **Objective:** Go Live on Railway.
- **Task 5.1:** Create `Dockerfile` and `railway.json`.
- **Task 5.2:** Set environment variables and Webhook URLs in Paystack/Meta dashboards.
