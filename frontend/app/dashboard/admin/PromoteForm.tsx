"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL!;

export default function PromoteForm() {
  const [identifier, setIdentifier] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; text: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!identifier.trim()) return;
    setLoading(true);
    setResult(null);

    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) return;

    const res = await fetch(`${BACKEND}/api/admin/promote`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ identifier: identifier.trim() }),
    });

    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      setResult({ type: "success", text: data.message ?? "User promoted." });
      setIdentifier("");
    } else {
      setResult({ type: "error", text: data.detail ?? "Promotion failed." });
    }
    setLoading(false);
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <input
        value={identifier}
        onChange={(e) => setIdentifier(e.target.value)}
        placeholder="Email or user UUID"
        className="flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
      />
      <button
        type="submit"
        disabled={loading}
        className="rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:opacity-50"
      >
        {loading ? "…" : "Promote"}
      </button>
      {result && (
        <p className={`mt-2 text-sm ${result.type === "success" ? "text-emerald-400" : "text-red-400"}`}>
          {result.text}
        </p>
      )}
    </form>
  );
}
