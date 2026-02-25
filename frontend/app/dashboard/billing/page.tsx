"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

interface Subscription {
  plan: string;
  amount: number;
  status: string;
  currency: string;
  created_at: string;
}

interface Profile {
  tier: string;
  email: string;
}

const PLANS = [
  { id: "pro_weekly", label: "Pro Weekly", price: "₦2,000", period: "/week", desc: "Billed weekly" },
  { id: "pro", label: "Pro Monthly", price: "₦7,000", period: "/month", desc: "Best value" },
];

export default function BillingPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const [profileRes, subsRes] = await Promise.all([
        supabase.from("profiles").select("tier, email").eq("id", session.user.id).maybeSingle(),
        supabase.from("subscriptions").select("plan, amount, status, currency, created_at")
          .eq("user_id", session.user.id).order("created_at", { ascending: false }).limit(10),
      ]);

      setProfile(profileRes.data ?? { tier: "free", email: session.user.email ?? "" });
      setSubs(subsRes.data ?? []);
      setLoading(false);
    }
    load();
  }, []);

  async function handleUpgrade(planId: string) {
    setPaying(planId);
    const res = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan: planId }),
    });
    const data = await res.json();
    if (data.url) {
      window.location.href = data.url;
    } else {
      alert("Payment initialization failed. Try again.");
      setPaying(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-2xl bg-white/5" />
        ))}
      </div>
    );
  }

  const tier = profile?.tier ?? "free";
  const isPro = tier === "pro" || tier === "elite";

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Billing</h1>
        <p className="mt-1 text-sm text-white/40">Manage your subscription and payments.</p>
      </div>

      {/* Current plan */}
      <div className="mb-6 flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 p-5">
        <div>
          <p className="text-xs text-white/40">Current Plan</p>
          <p className="mt-1 text-xl font-bold capitalize text-white">{tier}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
          isPro ? "bg-emerald-500/15 text-emerald-400" : "bg-white/10 text-white/50"
        }`}>
          {isPro ? "Active" : "Free"}
        </span>
      </div>

      {/* Upgrade section — only if not pro */}
      {!isPro && (
        <div className="mb-8">
          <h2 className="mb-4 text-sm font-semibold text-white/70">Upgrade to Pro</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {PLANS.map((plan) => (
              <div
                key={plan.id}
                className="relative rounded-2xl border border-white/10 bg-white/5 p-5"
              >
                {plan.id === "pro" && (
                  <span className="absolute right-4 top-4 rounded-full bg-emerald-500/20 px-2 py-0.5 text-xs text-emerald-400">
                    Best Value
                  </span>
                )}
                <p className="text-sm font-semibold text-white">{plan.label}</p>
                <p className="mt-1 text-2xl font-bold text-emerald-400">
                  {plan.price}
                  <span className="text-sm font-normal text-white/40">{plan.period}</span>
                </p>
                <p className="mt-0.5 text-xs text-white/30">{plan.desc}</p>
                <ul className="mt-3 space-y-1.5 text-xs text-white/60">
                  <li>✓ Unlimited alerts & pairs</li>
                  <li>✓ WhatsApp notifications</li>
                  <li>✓ Zone & correlation alerts</li>
                  <li>✓ Unlimited AI chat</li>
                </ul>
                <button
                  onClick={() => handleUpgrade(plan.id)}
                  disabled={paying === plan.id}
                  className="mt-4 w-full rounded-lg bg-emerald-500 py-2.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:opacity-50"
                >
                  {paying === plan.id ? "Redirecting..." : `Get ${plan.label}`}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Subscription history */}
      <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
        <h2 className="mb-4 text-sm font-semibold text-white/70">Payment History</h2>
        {subs.length === 0 ? (
          <p className="text-sm text-white/30">No payments yet.</p>
        ) : (
          <div className="space-y-3">
            {subs.map((s, i) => (
              <div key={i} className="flex items-center justify-between border-b border-white/5 pb-3 last:border-0 last:pb-0">
                <div>
                  <p className="text-sm capitalize text-white">{s.plan.replace("_", " ")}</p>
                  <p className="text-xs text-white/30">
                    {new Date(s.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-emerald-400">
                    {s.amount > 0 ? `₦${Number(s.amount).toLocaleString()}` : "Free"}
                  </p>
                  <span className={`text-xs ${s.status === "active" ? "text-emerald-400" : "text-white/30"}`}>
                    {s.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
