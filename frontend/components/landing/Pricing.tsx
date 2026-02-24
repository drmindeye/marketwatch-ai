"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { createClient } from "@/lib/supabase/client";

const plans = [
  {
    name: "Free",
    price: "₦0",
    period: "forever",
    description: "Get started with basic alerts",
    badge: null,
    plan: null,
    features: [
      "3 active price alerts",
      "Telegram notifications",
      "Basic market data",
      "Pip calculator",
    ],
    cta: "Get Started",
    href: "/signup",
    highlight: false,
  },
  {
    name: "Pro",
    price: "₦5,000",
    period: "/ month",
    description: "For serious traders",
    badge: "Most Popular",
    plan: "pro",
    features: [
      "Unlimited price alerts",
      "WhatsApp + Telegram alerts",
      "AI market summaries (Claude)",
      "Trade calculator (R/R + sizing)",
      "Priority alert delivery",
    ],
    cta: "Upgrade to Pro",
    href: null,
    highlight: true,
  },
  {
    name: "Elite",
    price: "₦15,000",
    period: "/ month",
    description: "For professional traders",
    badge: null,
    plan: "elite",
    features: [
      "Everything in Pro",
      "AI chat assistant (Claude)",
      "Custom alert logic",
      "Admin dashboard access",
      "Dedicated support",
    ],
    cta: "Go Elite",
    href: null,
    highlight: false,
  },
];

export default function Pricing() {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  async function handleCheckout(plan: string) {
    setLoading(plan);

    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();

    if (!session) {
      router.push(`/signup?plan=${plan}`);
      return;
    }

    const res = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan }),
    });

    const json = await res.json() as { url?: string; error?: string };

    if (json.url) {
      window.location.href = json.url;
    } else {
      alert(json.error ?? "Failed to start checkout. Please try again.");
      setLoading(null);
    }
  }

  return (
    <section id="pricing" className="px-6 py-24">
      <div className="mx-auto max-w-7xl">
        <div className="mb-16 text-center">
          <h2 className="text-4xl font-bold text-white">Simple Pricing</h2>
          <p className="mt-4 text-white/50">
            Start free. Upgrade when you need more power.
          </p>
        </div>

        <div className="grid gap-8 md:grid-cols-3">
          {plans.map((item) => (
            <div
              key={item.name}
              className={`relative flex flex-col rounded-2xl border p-8 ${
                item.highlight
                  ? "border-emerald-500/50 bg-emerald-500/5"
                  : "border-white/10 bg-white/5"
              }`}
            >
              {item.badge && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 border-emerald-500/30 bg-emerald-500 text-black">
                  {item.badge}
                </Badge>
              )}

              <div>
                <h3 className="text-lg font-semibold text-white">{item.name}</h3>
                <p className="mt-1 text-sm text-white/50">{item.description}</p>
                <div className="mt-4 flex items-end gap-1">
                  <span className="text-4xl font-bold text-white">{item.price}</span>
                  <span className="mb-1 text-white/40">{item.period}</span>
                </div>
              </div>

              <ul className="my-8 flex-1 space-y-3">
                {item.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-white/70">
                    <span className="mt-0.5 text-emerald-400">✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              {item.plan ? (
                <Button
                  onClick={() => handleCheckout(item.plan!)}
                  disabled={loading === item.plan}
                  className={
                    item.highlight
                      ? "bg-emerald-500 text-black hover:bg-emerald-400"
                      : "border border-white/20 bg-transparent text-white hover:bg-white/10"
                  }
                >
                  {loading === item.plan ? "Redirecting..." : item.cta}
                </Button>
              ) : (
                <Button
                  variant="outline"
                  className="border-white/20 text-white hover:bg-white/10"
                  asChild
                >
                  <Link href={item.href!}>{item.cta}</Link>
                </Button>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
