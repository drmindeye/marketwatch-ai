"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";

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

      const profile = data ?? {
        full_name: null,
        email: session.user.email ?? "",
        tier: "free",
        telegram_id: null,
        whatsapp: null,
      };
      setProfile(profile);
      setFullName(profile.full_name ?? "");
      setTelegramId(profile.telegram_id ?? "");
      setWhatsapp(profile.whatsapp ?? "");
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

    const { error } = await supabase
      .from("profiles")
      .update({
        full_name: fullName,
        telegram_id: telegramId || null,
        whatsapp: whatsapp || null,
      })
      .eq("id", session.user.id);

    if (error) {
      setMessage({ type: "error", text: error.message });
    } else {
      setMessage({ type: "success", text: "Profile updated successfully." });
    }
    setSaving(false);
  }

  if (!profile) {
    return <p className="text-sm text-white/30">Loading...</p>;
  }

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
            value={profile.tier}
            disabled
            className="w-full rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2.5 text-sm capitalize text-emerald-400 outline-none cursor-not-allowed"
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

        <div>
          <label className="mb-1.5 block text-xs text-white/50">Telegram ID</label>
          <input
            value={telegramId}
            onChange={(e) => setTelegramId(e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
            placeholder="e.g. 123456789"
          />
          <p className="mt-1.5 text-xs text-white/30">
            Get your ID by sending /start to{" "}
            <a
              href="https://t.me/marketwatchai_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="text-emerald-400 hover:underline"
            >
              @marketwatchai_bot
            </a>
          </p>
        </div>

        <div>
          <label className="mb-1.5 block text-xs text-white/50">
            WhatsApp Number{" "}
            <span className="text-white/20">(PRO/Elite only)</span>
          </label>
          <input
            value={whatsapp}
            onChange={(e) => setWhatsapp(e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
            placeholder="e.g. 2348012345678 (with country code, no +)"
          />
          <p className="mt-1.5 text-xs text-white/30">
            Include country code without + (e.g. 2348012345678 for Nigeria)
          </p>
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
