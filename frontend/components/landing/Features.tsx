const features = [
  {
    icon: "📊",
    title: "Real-Time Price Alerts",
    description:
      "Set Touch, Cross, or Near-Level alerts on any Forex pair, crypto, or stock. Powered by FMP batch quotes.",
  },
  {
    icon: "🤖",
    title: "AI Market Summaries",
    description:
      "Claude 3.5 Sonnet analyzes market conditions and delivers plain-English trade context with every alert.",
  },
  {
    icon: "📱",
    title: "WhatsApp & Telegram",
    description:
      "PRO users get instant WhatsApp notifications. All users get Telegram alerts. Zero delay, zero noise.",
  },
  {
    icon: "🧮",
    title: "Trade Calculator",
    description:
      "Built-in Risk/Reward, Position Sizing, and Pip calculator. Know your exposure before you enter.",
  },
  {
    icon: "🔒",
    title: "Secure Payments",
    description:
      "Paystack integration with HMAC SHA512 webhook verification. Your payments are safe and auditable.",
  },
  {
    icon: "⚡",
    title: "Sub-Second Delivery",
    description:
      "FastAPI background workers poll FMP every 30 seconds. Alerts fire within seconds of your level being hit.",
  },
];

export default function Features() {
  return (
    <section id="features" className="px-6 py-24">
      <div className="mx-auto max-w-7xl">
        <div className="mb-16 text-center">
          <h2 className="text-4xl font-bold text-white">Everything You Need</h2>
          <p className="mt-4 text-white/50">
            Professional-grade market monitoring without the complexity.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-white/10 bg-white/5 p-6 transition hover:border-emerald-500/30 hover:bg-white/8"
            >
              <span className="text-3xl">{f.icon}</span>
              <h3 className="mt-4 text-lg font-semibold text-white">{f.title}</h3>
              <p className="mt-2 text-sm text-white/50">{f.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
