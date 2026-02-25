const secondaryFeatures = [
  {
    icon: "⚡",
    title: "4 Alert Types",
    description:
      "Touch — price hits a level. Cross — price breaks through. Near — within X pips of a level. Zone — price enters your range.",
  },
  {
    icon: "📊",
    title: "Multi-Pair Watchlist",
    description:
      "Watch correlated pairs simultaneously — EURUSD + GBPUSD, XAUUSD + DXY. Set alerts across your full watchlist.",
  },
  {
    icon: "🤖",
    title: "AI Market Context",
    description:
      "Every alert comes with a plain-English market summary from DeepSeek AI — so you know why the level matters.",
  },
  {
    icon: "📱",
    title: "Telegram & WhatsApp",
    description:
      "Free users get instant Telegram alerts. Pro users unlock WhatsApp too. Zero delay, zero missed trades.",
  },
  {
    icon: "🧮",
    title: "Trade Calculator",
    description:
      "Built-in Risk/Reward, Position Sizing, and Pip calculator. Know your exact exposure before you enter.",
  },
  {
    icon: "🔄",
    title: "Sub-30s Delivery",
    description:
      "Background workers poll live market data every 30 seconds. Alerts fire within seconds of your level being hit.",
  },
];

function ZoneDiagram() {
  return (
    <div className="relative h-52 w-full overflow-hidden rounded-xl border border-white/10 bg-zinc-950">
      {/* Zone band */}
      <div
        className="absolute inset-x-0 border-y border-emerald-500/50 bg-emerald-500/10"
        style={{ top: "33%", height: "27%" }}
      />

      {/* Zone labels */}
      <span
        className="absolute right-3 text-xs text-emerald-400"
        style={{ top: "28%" }}
      >
        Zone High — 1.0870
      </span>
      <span
        className="absolute right-3 text-xs text-emerald-400"
        style={{ top: "62%" }}
      >
        Zone Low — 1.0840
      </span>

      {/* Old single-level dashed line */}
      <div
        className="absolute inset-x-0"
        style={{
          top: "20%",
          borderTop: "1px dashed rgba(255,255,255,0.12)",
        }}
      >
        <span
          className="absolute left-3 text-xs text-white/25"
          style={{ top: "-16px" }}
        >
          ← single-level alert (missed by 2 pips)
        </span>
      </div>

      {/* Price line SVG */}
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 300 100"
        preserveAspectRatio="none"
      >
        <polyline
          points="0,12 40,15 80,10 120,18 150,22 180,28 205,34 228,44 255,46 285,44"
          fill="none"
          stroke="rgba(255,255,255,0.45)"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>

      {/* Alert badge — appears where price enters zone */}
      <div
        className="absolute flex -translate-x-1/2 flex-col items-center gap-1"
        style={{ left: "69%", top: "36%" }}
      >
        <div className="animate-bounce rounded-full bg-emerald-500 px-2.5 py-0.5 text-xs font-bold text-black shadow-lg shadow-emerald-500/40">
          Alert fired!
        </div>
      </div>

      {/* Label: price line */}
      <span className="absolute bottom-3 left-3 text-xs text-white/30">
        Price action
      </span>
    </div>
  );
}

export default function Features() {
  return (
    <section id="features" className="px-6 py-24">
      <div className="mx-auto max-w-7xl">

        {/* ── Zone Alert Hero Card ───────────────────────────────────────── */}
        <div className="mb-24 overflow-hidden rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-8 md:p-12">
          <div className="grid gap-10 md:grid-cols-2 md:items-center">
            <div>
              <span className="mb-4 inline-block rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-emerald-400">
                Flagship Feature
              </span>
              <h2 className="text-3xl font-bold text-white md:text-4xl">
                Zone Alerts — the last 2 pips won&apos;t cost you again.
              </h2>
              <p className="mt-4 text-white/60">
                Single-level alerts fail when price reverses just before your
                entry. Zone alerts cover the entire region — set a low and a
                high, get alerted the moment price steps inside from any
                direction.
              </p>
              <ul className="mt-6 space-y-2 text-sm text-white/60">
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span>
                  Perfect for order blocks, supply/demand zones &amp; S/R ranges
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span>
                  Works on every Forex pair, crypto, and commodity
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span>
                  Pro feature — unlimited zones across unlimited pairs
                </li>
              </ul>
            </div>
            <ZoneDiagram />
          </div>
        </div>

        {/* ── Secondary Features Grid ───────────────────────────────────── */}
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold text-white">Everything Else You Need</h2>
          <p className="mt-3 text-white/50">
            Professional-grade tools, zero complexity.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {secondaryFeatures.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-white/10 bg-white/5 p-6 transition hover:border-emerald-500/30 hover:bg-white/[0.08]"
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
