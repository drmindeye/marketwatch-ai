"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL!;

// Correlation groups — hardcoded relationships, live prices fetched
const GROUPS = [
  {
    id: "dollar",
    label: "Dollar-Denominated Pairs",
    description:
      "These pairs move in the same direction. When the Euro strengthens, the British Pound and Aussie typically follow.",
    correlation: "positive" as const,
    pairs: [
      { symbol: "EURUSD", name: "Euro / USD" },
      { symbol: "GBPUSD", name: "British Pound / USD" },
      { symbol: "AUDUSD", name: "Australian Dollar / USD" },
      { symbol: "NZDUSD", name: "New Zealand Dollar / USD" },
    ],
  },
  {
    id: "safehaven",
    label: "Safe Haven vs Risk",
    description:
      "Gold (XAUUSD) and JPY tend to rise when markets are fearful. They often move opposite to risk-on pairs.",
    correlation: "mixed" as const,
    pairs: [
      { symbol: "XAUUSD", name: "Gold / USD" },
      { symbol: "USDJPY", name: "USD / Japanese Yen" },
      { symbol: "USDCHF", name: "USD / Swiss Franc" },
    ],
  },
  {
    id: "risk",
    label: "Risk-On Assets",
    description:
      "Crypto and commodity currencies tend to rally together during risk-on environments.",
    correlation: "positive" as const,
    pairs: [
      { symbol: "BTCUSD", name: "Bitcoin / USD" },
      { symbol: "ETHUSD", name: "Ethereum / USD" },
      { symbol: "AUDUSD", name: "Australian Dollar / USD" },
      { symbol: "USDCAD", name: "USD / Canadian Dollar" },
    ],
  },
];

const ALL_SYMBOLS = [...new Set(GROUPS.flatMap((g) => g.pairs.map((p) => p.symbol)))];

interface PriceData {
  price: number | null;
  change: number;
  name: string;
}

const corr_badge = {
  positive: { label: "Positive", className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
  mixed:    { label: "Inverse / Mixed", className: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
};

export default function CorrelationPage() {
  const [prices, setPrices] = useState<Record<string, PriceData>>({});
  const [loading, setLoading] = useState(true);
  const [tier, setTier] = useState<string>("free");

  useEffect(() => {
    async function load() {
      // Get tier
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        const { data: profile } = await supabase
          .from("profiles")
          .select("tier")
          .eq("id", session.user.id)
          .maybeSingle();
        setTier(profile?.tier ?? "free");
      }

      // Fetch prices
      try {
        const res = await fetch(
          `${BACKEND}/api/market/prices?symbols=${ALL_SYMBOLS.join(",")}`,
          { cache: "no-store" }
        );
        if (res.ok) setPrices(await res.json());
      } catch {
        // silently fail — prices just won't show
      }
      setLoading(false);
    }
    load();
  }, []);

  const isPro = tier === "pro" || tier === "elite";

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Pair Correlation</h1>
        <p className="mt-2 text-sm text-white/50">
          Understand how pairs move together. Use this to confirm setups or
          avoid over-exposure on correlated positions.
        </p>
      </div>

      {!isPro && (
        <div className="mb-8 flex items-center justify-between gap-4 rounded-xl border border-amber-500/20 bg-amber-500/5 px-5 py-4">
          <p className="text-sm text-amber-300">
            Zone alerts across correlated pairs are a <strong>Pro feature</strong>. Upgrade to set zone alerts on multiple pairs at once.
          </p>
          <a
            href="/dashboard/settings"
            className="flex-shrink-0 rounded-lg bg-amber-500 px-4 py-1.5 text-xs font-semibold text-black hover:bg-amber-400 transition"
          >
            Upgrade
          </a>
        </div>
      )}

      <div className="space-y-8">
        {GROUPS.map((group) => {
          const badge = corr_badge[group.correlation];
          return (
            <div
              key={group.id}
              className="rounded-2xl border border-white/10 bg-white/5 p-6"
            >
              <div className="mb-1 flex flex-wrap items-center gap-3">
                <h2 className="text-lg font-semibold text-white">{group.label}</h2>
                <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${badge.className}`}>
                  {badge.label}
                </span>
              </div>
              <p className="mb-5 text-sm text-white/45">{group.description}</p>

              <div className="grid gap-3 sm:grid-cols-2">
                {group.pairs.map((pair) => {
                  const data = prices[pair.symbol];
                  const change = data?.change ?? 0;
                  const positive = change >= 0;
                  return (
                    <div
                      key={pair.symbol}
                      className="flex items-center justify-between rounded-xl border border-white/8 bg-black/30 px-4 py-3"
                    >
                      <div>
                        <p className="font-mono text-sm font-semibold text-white">
                          {pair.symbol}
                        </p>
                        <p className="text-xs text-white/40">{pair.name}</p>
                      </div>
                      <div className="text-right">
                        {loading ? (
                          <div className="h-4 w-20 animate-pulse rounded bg-white/10" />
                        ) : data?.price ? (
                          <>
                            <p className="font-mono text-sm text-white">
                              {data.price.toFixed(pair.symbol.includes("JPY") ? 3 : pair.symbol === "BTCUSD" || pair.symbol === "ETHUSD" ? 2 : 5)}
                            </p>
                            <p className={`text-xs font-medium ${positive ? "text-emerald-400" : "text-red-400"}`}>
                              {positive ? "+" : ""}{change.toFixed(2)}%
                            </p>
                          </>
                        ) : (
                          <p className="text-xs text-white/25">unavailable</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-6 text-center text-xs text-white/20">
        Prices refresh on page load · Powered by Financial Modeling Prep
      </p>
    </div>
  );
}
