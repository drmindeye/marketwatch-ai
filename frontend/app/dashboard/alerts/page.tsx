"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL;

interface Alert {
  id: string;
  symbol: string;
  alert_type: string;
  price: number;
  direction: string | null;
  pip_buffer: number;
  is_active: boolean;
  triggered_at: string | null;
  created_at: string;
}

const ALERT_TYPES = ["touch", "cross", "near"];
const DIRECTIONS = ["above", "below"];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [symbol, setSymbol] = useState("EURUSD");
  const [alertType, setAlertType] = useState("touch");
  const [price, setPrice] = useState("");
  const [direction, setDirection] = useState("above");
  const [pipBuffer, setPipBuffer] = useState("5");

  async function getToken(): Promise<string> {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token ?? "";
  }

  async function loadAlerts() {
    setLoading(true);
    const token = await getToken();
    const res = await fetch(`${BACKEND}/api/alerts`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setAlerts(await res.json());
    setLoading(false);
  }

  async function createAlert(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    const token = await getToken();

    const res = await fetch(`${BACKEND}/api/alerts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        symbol: symbol.toUpperCase(),
        alert_type: alertType,
        price: parseFloat(price),
        direction: alertType === "near" ? null : direction,
        pip_buffer: parseFloat(pipBuffer),
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      setError(data.detail ?? "Failed to create alert");
    } else {
      setShowForm(false);
      setPrice("");
      await loadAlerts();
    }
    setCreating(false);
  }

  async function deleteAlert(id: string) {
    const token = await getToken();
    await fetch(`${BACKEND}/api/alerts/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }

  useEffect(() => { loadAlerts(); }, []);

  return (
    <div className="max-w-3xl">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Price Alerts</h1>
          <p className="mt-1 text-sm text-white/40">
            Get notified when your price levels are hit.
          </p>
        </div>
        <Button
          onClick={() => setShowForm(!showForm)}
          className="bg-emerald-500 text-black hover:bg-emerald-400"
        >
          {showForm ? "Cancel" : "+ New Alert"}
        </Button>
      </div>

      {/* Create form */}
      {showForm && (
        <form
          onSubmit={createAlert}
          className="mb-8 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6"
        >
          <h2 className="mb-4 font-semibold text-white">New Alert</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-xs text-white/50">Symbol</label>
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
                placeholder="EURUSD"
                required
              />
            </div>

            <div>
              <label className="mb-1.5 block text-xs text-white/50">Alert Type</label>
              <select
                value={alertType}
                onChange={(e) => setAlertType(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-black px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
              >
                {ALERT_TYPES.map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs text-white/50">Price Level</label>
              <input
                type="number"
                step="any"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
                placeholder="1.10500"
                required
              />
            </div>

            {alertType !== "near" && (
              <div>
                <label className="mb-1.5 block text-xs text-white/50">Direction</label>
                <select
                  value={direction}
                  onChange={(e) => setDirection(e.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-black px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
                >
                  {DIRECTIONS.map((d) => (
                    <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
                  ))}
                </select>
              </div>
            )}

            {alertType === "near" && (
              <div>
                <label className="mb-1.5 block text-xs text-white/50">Pip Buffer</label>
                <input
                  type="number"
                  value={pipBuffer}
                  onChange={(e) => setPipBuffer(e.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
                  placeholder="5"
                />
              </div>
            )}
          </div>

          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

          <Button
            type="submit"
            disabled={creating}
            className="mt-4 bg-emerald-500 text-black hover:bg-emerald-400"
          >
            {creating ? "Creating..." : "Create Alert"}
          </Button>
        </form>
      )}

      {/* Alerts list */}
      {loading ? (
        <p className="text-sm text-white/30">Loading alerts...</p>
      ) : alerts.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-10 text-center">
          <p className="text-3xl">🔔</p>
          <p className="mt-3 text-white/40">No alerts yet. Create your first one above.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`flex items-center justify-between rounded-2xl border p-4 ${
                alert.triggered_at
                  ? "border-white/5 bg-white/[0.02] opacity-50"
                  : "border-white/10 bg-white/5"
              }`}
            >
              <div className="flex items-center gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white">{alert.symbol}</span>
                    <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs capitalize text-white/60">
                      {alert.alert_type}
                    </span>
                    {alert.direction && (
                      <span className={`rounded-full px-2 py-0.5 text-xs ${
                        alert.direction === "above"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : "bg-red-500/10 text-red-400"
                      }`}>
                        {alert.direction}
                      </span>
                    )}
                    {alert.triggered_at && (
                      <span className="rounded-full bg-purple-500/10 px-2 py-0.5 text-xs text-purple-400">
                        triggered
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-sm text-white/50">
                    Level: <span className="text-white">{alert.price}</span>
                    {alert.alert_type === "near" && (
                      <span className="ml-2 text-white/30">± {alert.pip_buffer} pips</span>
                    )}
                  </p>
                </div>
              </div>

              {!alert.triggered_at && (
                <button
                  onClick={() => deleteAlert(alert.id)}
                  className="ml-4 text-xs text-white/20 hover:text-red-400 transition"
                >
                  Delete
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
