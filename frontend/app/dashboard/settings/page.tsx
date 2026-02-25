"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL!;

interface Profile {
  full_name: string | null;
  email: string;
  tier: string;
  telegram_id: string | null;
  whatsapp: string | null;
}

export default function SettingsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [fullName, setFullName] = useState("");
  const [telegramId, setTelegramId] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const { data } = await supabase
        .from("profiles")
        .select("full_name, email, tier, telegram_id, whatsapp")
        .eq("id", session.user.id)
        .maybeSingle();

      const p = data ?? {
        full_name: null,
        email: session.user.email ?? "",
        tier: "free",
        telegram_id: null,
        whatsapp: null,
      };
      setProfile(p);
      setFullName(p.full_name ?? "");
      setTelegramId(p.telegram_id ?? "");
      setWhatsapp(p.whatsapp ?? "");
    }
    load();
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) return;

    // Update full_name via Supabase directly
    await supabase
      .from("profiles")
      .update({ full_name: fullName })
      .eq("id", session.user.id);

    // Link Telegram + WhatsApp via backend (sends Telegram confirmation)
    const res = await fetch(`${BACKEND}/api/profile/link`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        telegram_id: telegramId || null,
        whatsapp: whatsapp || null,
      }),
    });

    if (res.ok) {
      setMessage({
        type: "success",
        text: telegramId
          ? "Saved! Check Telegram — we sent you a confirmation message."
          : "Profile updated successfully.",
      });
      setProfile((p) => p ? { ...p, telegram_id: telegramId || null, whatsapp: whatsapp || null } : p);
    } else {
      const err = await res.json().catch(() => ({}));
      setMessage({ type: "error", text: err.detail ?? "Save failed." });
    }
    setSaving(false);
  }

  if (!profile) {
    return <p className="text-sm text-white/30">Loading...</p>;
  }

  const isLinked = !!profile.telegram_id;

  return (
    <div className="max-w-lg">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Profile Settings</h1>
        <p className="mt-1 text-sm text-white/40">
          Update your notification channels and account details.
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-5">
        {/* Read-only */}
        <div>
          <label className="mb-1.5 block text-xs text-white/50">Email</label>
          <input
            value={profile.email}
            disabled
            className="w-full rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2.5 text-sm text-white/40 outline-none cursor-not-allowed"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs text-white/50">Plan</label>
          <input
            value={profile.tier.toUpperCase()}
            disabled
            className="w-full rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2.5 text-sm text-emerald-400 outline-none cursor-not-allowed"
          />
        </div>

        {/* Editable */}
        <div>
          <label className="mb-1.5 block text-xs text-white/50">Full Name</label>
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
            placeholder="John Doe"
          />
        </div>

        {/* Telegram — auto-link */}
        <div className="rounded-xl border border-white/10 bg-white/5 p-4">
          <div className="mb-3 flex items-center justify-between">
            <label className="text-xs font-semibold text-white/70">Telegram ID</label>
            {isLinked ? (
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-400">
                ✓ Linked
              </span>
            ) : (
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/40">
                Not linked
              </span>
            )}
          </div>
          <input
            value={telegramId}
            onChange={(e) => setTelegramId(e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
            placeholder="e.g. 123456789"
          />
          <div className="mt-2.5 space-y-1 text-xs text-white/40">
            <p>
              1. Open{" "}
              <a href="https://t.me/marketwatchai_bot" target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">
                @marketwatchai_bot
              </a>{" "}
              and press <strong className="text-white/60">Start</strong>
            </p>
            <p>2. Type <code className="text-emerald-300">/id</code> — copy the number shown</p>
            <p>3. Paste it above and save — you&apos;ll get a confirmation in Telegram instantly</p>
          </div>
        </div>

        {/* WhatsApp */}
        <div>
          <label className="mb-1.5 block text-xs text-white/50">
            WhatsApp Number{" "}
            <span className="text-white/20">(Pro only)</span>
          </label>
          <input
            value={whatsapp}
            onChange={(e) => setWhatsapp(e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
            placeholder="e.g. 2348012345678 (country code, no +)"
          />
        </div>

        {message && (
          <p className={`text-sm ${message.type === "success" ? "text-emerald-400" : "text-red-400"}`}>
            {message.text}
          </p>
        )}

        <Button
          type="submit"
          disabled={saving}
          className="w-full bg-emerald-500 text-black hover:bg-emerald-400"
        >
          {saving ? "Saving..." : "Save Changes"}
        </Button>
      </form>
    </div>
  );
}
