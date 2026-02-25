"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { createClient } from "@/lib/supabase/client";

const freeFeatures = [
  "1 trading pair",
  "2 alerts per day",
  "Touch, Cross & Near alert types",
  "Telegram notifications",
  "Trade calculator",
];

const proFeatures = [
  "Unlimited trading pairs",
  "Unlimited alerts",
  "Zone alerts (flagship feature)",
  "Telegram + WhatsApp alerts",
  "AI market context per alert",
  "Trade calculator",
];

export default function Pricing() {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);
  const [billing, setBilling] = useState<"monthly" | "weekly">("monthly");

  async function handleCheckout(plan: string) {
    setLoading(plan);
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      router.push(`/signup?plan=${plan}`);
      return;
    }

    const res = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan }),
    });

    const json = (await res.json()) as { url?: string; error?: string };

    if (json.url) {
      window.location.href = json.url;
    } else {
      alert(json.error ?? "Failed to start checkout. Please try again.");
      setLoading(null);
    }
  }

  const proPrice = billing === "monthly" ? "₦7,000" : "₦2,000";
  const proPeriod = billing === "monthly" ? "/ month" : "/ week";
  const proPlan = billing === "monthly" ? "pro" : "pro_weekly";

  return (
    <section id="pricing" className="px-6 py-24">
      <div className="mx-auto max-w-4xl">
        <div className="mb-16 text-center">
          <h2 className="text-4xl font-bold text-white">Simple Pricing</h2>
          <p className="mt-4 text-white/50">
            Start free on Telegram. Unlock everything with Pro.
          </p>
        </div>

        <div className="grid gap-8 md:grid-cols-2">
          {/* ── Free ─────────────────────────────────────────────────────── */}
          <div className="flex flex-col rounded-2xl border border-white/10 bg-white/5 p-8">
            <div>
              <h3 className="text-lg font-semibold text-white">Free</h3>
              <p className="mt-1 text-sm text-white/50">
                Get started, no card needed
              </p>
              <div className="mt-4 flex items-end gap-1">
                <span className="text-4xl font-bold text-white">₦0</span>
                <span className="mb-1 text-white/40">forever</span>
              </div>
            </div>

            <ul className="my-8 flex-1 space-y-3">
              {freeFeatures.map((f) => (
                <li
                  key={f}
                  className="flex items-start gap-2 text-sm text-white/70"
                >
                  <span className="mt-0.5 text-emerald-400">✓</span>
                  {f}
                </li>
              ))}
            </ul>

            <Button
              variant="outline"
              className="border-white/20 text-white hover:bg-white/10"
              asChild
            >
              <Link href="/signup">Get Started</Link>
            </Button>
          </div>

          {/* ── Pro ──────────────────────────────────────────────────────── */}
          <div className="relative flex flex-col rounded-2xl border border-emerald-500/50 bg-emerald-500/5 p-8">
            <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 border-emerald-500/30 bg-emerald-500 text-black">
              Most Popular
            </Badge>

            <div>
              <h3 className="text-lg font-semibold text-white">Pro</h3>
              <p className="mt-1 text-sm text-white/50">For serious traders</p>

              {/* Billing toggle */}
              <div className="mt-4 flex items-center gap-2">
                <button
                  onClick={() => setBilling("monthly")}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                    billing === "monthly"
                      ? "bg-emerald-500 text-black"
                      : "border border-white/20 text-white/60 hover:text-white"
                  }`}
                >
                  Monthly
                </button>
                <button
                  onClick={() => setBilling("weekly")}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                    billing === "weekly"
                      ? "bg-emerald-500 text-black"
                      : "border border-white/20 text-white/60 hover:text-white"
                  }`}
                >
                  Weekly
                </button>
              </div>

              <div className="mt-3 flex items-end gap-1">
                <span className="text-4xl font-bold text-white">{proPrice}</span>
                <span className="mb-1 text-white/40">{proPeriod}</span>
              </div>
            </div>

            <ul className="my-8 flex-1 space-y-3">
              {proFeatures.map((f) => (
                <li
                  key={f}
                  className="flex items-start gap-2 text-sm text-white/70"
                >
                  <span className="mt-0.5 text-emerald-400">✓</span>
                  {f}
                </li>
              ))}
            </ul>

            <Button
              onClick={() => handleCheckout(proPlan)}
              disabled={loading !== null}
              className="bg-emerald-500 text-black hover:bg-emerald-400"
            >
              {loading !== null ? "Redirecting..." : "Upgrade to Pro"}
            </Button>
          </div>
        </div>

        <p className="mt-8 text-center text-sm text-white/30">
          Payments processed securely by Paystack · Cancel anytime
        </p>
      </div>
    </section>
  );
}
