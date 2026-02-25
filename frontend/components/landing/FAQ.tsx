const faqs = [
  {
    q: "What exactly is a Zone Alert?",
    a: "A Zone Alert lets you define a price range — a low and a high — instead of a single price level. When price enters that range from either direction, you get notified immediately. This is perfect for order blocks, supply/demand zones, and any S/R region where you don't know the exact pip price will react from.",
  },
  {
    q: "How do I set up the Telegram bot?",
    a: "Sign up on the website, then open @marketwatchai_bot on Telegram and send the command: /link your@email.com — your account links instantly. From there you can create alerts, run the trade calculator, and chat with the AI, all without leaving Telegram.",
  },
  {
    q: "What markets are supported?",
    a: "Forex pairs (EURUSD, GBPUSD, USDJPY, etc.), crypto (BTCUSD, ETHUSD), gold (XAUUSD), and major commodities. Market data is powered by Financial Modeling Prep and refreshes every 30 seconds.",
  },
  {
    q: "How quickly do alerts fire after a level is hit?",
    a: "The background engine polls live prices every 30 seconds. In most cases you'll be notified within 30 seconds of price touching or entering your level — fast enough for swing and intraday setups.",
  },
  {
    q: "What's the difference between Free and Pro?",
    a: "Free gives you 1 trading pair and up to 2 alerts per day, delivered via Telegram. Pro unlocks unlimited pairs, unlimited daily alerts, Zone alerts, WhatsApp delivery, and AI market context attached to every alert.",
  },
  {
    q: "Why is WhatsApp only available on Pro?",
    a: "WhatsApp Business API charges per message sent. To keep the free tier sustainable for everyone, WhatsApp notifications are reserved for Pro members. Telegram is free, equally fast, and available on all plans.",
  },
  {
    q: "Can I cancel my Pro subscription anytime?",
    a: "Yes. Reach out to support and we'll cancel it immediately. Your Pro access stays active until the end of the current billing period — no partial refunds, no lock-in.",
  },
  {
    q: "Is my payment secure?",
    a: "All payments are handled by Paystack, one of Africa's leading payment processors. We verify every transaction with HMAC SHA512 signatures. Your card details are never stored on our servers.",
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
