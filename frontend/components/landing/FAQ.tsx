const faqs = [
  {
    q: "What exactly is a Zone Alert?",
    a: "A Zone Alert lets you define a price range — a low and a high — instead of a single price level. When price enters that range from either direction, you get notified immediately. Perfect for order blocks, supply/demand zones, and BTC/ETH key ranges where you don't know the exact level price will react from.",
  },
  {
    q: "Does this work for crypto, not just Forex?",
    a: "Yes — fully. Set alerts on BTCUSD, ETHUSD, or any FMP-supported crypto asset just like you would on EURUSD. Zone alerts, AI context, session reminders, and correlation groups all work across Forex and crypto.",
  },
  {
    q: "What are Session Reminders?",
    a: "Session reminders ping you when a trading session opens — Asian at 00:00 UTC, London at 08:00 UTC, New York at 13:00 UTC. You can also set custom reminders: just tell the bot 'remind me at 9pm to check my BTCUSD trade' and it will. All via Telegram.",
  },
  {
    q: "How do I set up the bot?",
    a: "Two ways: (1) Sign up → go to Settings → enter your Telegram ID (from /id in the bot) → save. You'll get an instant confirmation in Telegram. Or (2) open @marketwatchai_bot and send /link your@email.com. That's it — fully linked in under a minute.",
  },
  {
    q: "What markets are supported?",
    a: "Forex pairs (EURUSD, GBPUSD, USDJPY, etc.), major crypto (BTCUSD, ETHUSD), gold (XAUUSD), and other FMP-supported assets. Data refreshes every 30 seconds.",
  },
  {
    q: "How quickly do alerts fire?",
    a: "The background engine polls live prices every 30 seconds. In most cases you're notified within 30 seconds of price touching or entering your level — fast enough for swing and intraday setups on both Forex and crypto.",
  },
  {
    q: "What's the difference between Free and Pro?",
    a: "Free gives you 1 trading pair, 2 alerts per day, and Telegram notifications. Pro unlocks unlimited pairs and alerts, Zone alerts, WhatsApp delivery, correlation groups, unlimited AI chat, and session reminders.",
  },
  {
    q: "Is my payment secure?",
    a: "All payments go through Paystack, Africa's leading payment processor. We verify every transaction with HMAC SHA512 signatures. Your card details are never stored on our servers.",
  },
];

export default function FAQ() {
  return (
    <section id="faq" className="px-6 py-24">
      <div className="mx-auto max-w-3xl">
        <div className="mb-14 text-center">
          <h2 className="text-4xl font-bold text-white">
            Frequently Asked Questions
          </h2>
          <p className="mt-4 text-white/50">
            Everything you need to know before you start.
          </p>
        </div>

        <div className="space-y-3">
          {faqs.map((item) => (
            <details
              key={item.q}
              className="group rounded-xl border border-white/10 bg-white/5 px-6 py-1 transition hover:border-white/20"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 text-sm font-semibold text-white marker:hidden">
                {item.q}
                {/* chevron — rotates when open */}
                <span className="flex-shrink-0 text-white/40 transition-transform duration-200 group-open:rotate-180">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    aria-hidden="true"
                  >
                    <path
                      d="M4 6l4 4 4-4"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </summary>
              <p className="pb-5 text-sm leading-relaxed text-white/55">
                {item.a}
              </p>
            </details>
          ))}
        </div>

        <p className="mt-10 text-center text-sm text-white/30">
          Still have questions?{" "}
          <a
            href="https://t.me/MarketWatchSupport"
            target="_blank"
            rel="noopener noreferrer"
            className="text-emerald-400 underline-offset-4 hover:underline"
          >
            Message us on Telegram
          </a>
        </p>
      </div>
    </section>
  );
}
