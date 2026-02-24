import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export default async function HistoryPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  const { data: alerts } = await supabase
    .from("alerts")
    .select("*")
    .eq("user_id", session.user.id)
    .not("triggered_at", "is", null)
    .order("triggered_at", { ascending: false });

  const TYPE_EMOJI: Record<string, string> = {
    touch: "🎯",
    cross: "⚡",
    near: "📍",
  };

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Alert History</h1>
        <p className="mt-1 text-sm text-white/40">
          All your triggered price alerts.
        </p>
      </div>

      {!alerts || alerts.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-10 text-center">
          <p className="text-3xl">📭</p>
          <p className="mt-3 text-white/40">No triggered alerts yet.</p>
          <p className="mt-1 text-sm text-white/20">
            Create alerts and they&apos;ll appear here once triggered.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 p-4"
            >
              <div className="flex items-center gap-4">
                <span className="text-2xl">
                  {TYPE_EMOJI[alert.alert_type] ?? "🔔"}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white">
                      {alert.symbol}
                    </span>
                    <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs capitalize text-white/60">
                      {alert.alert_type}
                    </span>
                    {alert.direction && (
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          alert.direction === "above"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : "bg-red-500/10 text-red-400"
                        }`}
                      >
                        {alert.direction}
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-sm text-white/50">
                    Target:{" "}
                    <span className="text-white">{alert.price}</span>
                    {alert.alert_type === "near" && (
                      <span className="ml-2 text-white/30">
                        ± {alert.pip_buffer} pips
                      </span>
                    )}
                  </p>
                </div>
              </div>

              <div className="text-right">
                <p className="text-xs text-white/30">Triggered</p>
                <p className="mt-0.5 text-sm text-white/60">
                  {new Date(alert.triggered_at).toLocaleDateString("en-GB", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </p>
                <p className="text-xs text-white/30">
                  {new Date(alert.triggered_at).toLocaleTimeString("en-GB", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
