"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL!;

interface ReferralData {
  code: string;
  count: number;
  link: string;
  reward: string;
}

export default function ReferralPage() {
  const [data, setData] = useState<ReferralData | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const res = await fetch(`${BACKEND}/api/referral`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) setData(await res.json());
      setLoading(false);
    }
    load();
  }, []);

  function copy() {
    if (!data?.link) return;
    navigator.clipboard.writeText(data.link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Refer & Earn</h1>
        <p className="mt-2 text-sm text-white/50">
          Share your referral link. Earn 1 week of Pro free for every friend
          who upgrades to Pro.
        </p>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-2xl bg-white/5" />
          ))}
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Stats */}
          <div className="grid gap-4 sm:grid-cols-2">
            <Stat label="Your Referrals" value={data.count.toString()} accent />
            <Stat label="Weeks Earned" value={data.count.toString()} />
          </div>

          {/* Referral link */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <p className="mb-3 text-sm font-semibold text-white">Your Referral Link</p>
            <div className="flex items-center gap-3">
              <code className="flex-1 truncate rounded-lg border border-white/10 bg-black/40 px-4 py-2.5 text-sm text-emerald-300">
                {data.link}
              </code>
              <button
                onClick={copy}
                className="flex-shrink-0 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-emerald-400"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          </div>

          {/* How it works */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <p className="mb-4 text-sm font-semibold text-white">How It Works</p>
            <div className="space-y-3">
              {[
                { step: "1", text: "Share your link with other traders." },
                {
                  step: "2",
                  text: "They sign up and upgrade to Pro (any plan).",
                },
                {
                  step: "3",
                  text: "You get 1 free week of Pro — automatically credited.",
                },
              ].map(({ step, text }) => (
                <div key={step} className="flex items-start gap-3">
                  <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-xs font-bold text-emerald-400">
                    {step}
                  </span>
                  <p className="text-sm text-white/60">{text}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Referral code */}
          <p className="text-center text-xs text-white/30">
            Your referral code:{" "}
            <span className="font-mono text-white/50">{data.code}</span>
          </p>
        </div>
      ) : (
        <p className="text-sm text-white/40">Could not load referral data.</p>
      )}
    </div>
  );
}

function Stat({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
      <p className="text-sm text-white/40">{label}</p>
      <p className={`mt-2 text-4xl font-bold ${accent ? "text-emerald-400" : "text-white"}`}>
        {value}
      </p>
    </div>
  );
}
