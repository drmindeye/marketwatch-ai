import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

interface TierCount {
  tier: string;
  count: number;
}

interface RevenueRow {
  amount: number;
}

export default async function AdminPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) redirect("/login");

  // Only elite tier gets admin access
  const { data: profile } = await supabase
    .from("profiles")
    .select("tier, full_name")
    .eq("id", session.user.id)
    .single();

  if (profile?.tier !== "elite") {
    redirect("/dashboard");
  }

  // Tier breakdown
  const { data: profiles } = await supabase
    .from("profiles")
    .select("tier");

  const tierCounts = (profiles ?? []).reduce<Record<string, number>>((acc, p) => {
    acc[p.tier] = (acc[p.tier] ?? 0) + 1;
    return acc;
  }, {});

  const totalUsers = (profiles ?? []).length;

  // Revenue from active subscriptions
  const { data: subscriptions } = await supabase
    .from("subscriptions")
    .select("amount, plan, status, created_at")
    .eq("status", "active")
    .order("created_at", { ascending: false });

  const totalRevenue = (subscriptions ?? []).reduce(
    (sum: number, s: RevenueRow) => sum + Number(s.amount),
    0
  );

  const tiers: TierCount[] = [
    { tier: "free", count: tierCounts["free"] ?? 0 },
    { tier: "pro", count: tierCounts["pro"] ?? 0 },
    { tier: "elite", count: tierCounts["elite"] ?? 0 },
  ];

  return (
    <div className="min-h-screen bg-black px-6 py-12 text-white">
      <div className="mx-auto max-w-5xl">

        {/* Header */}
        <div className="mb-10 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Admin Dashboard</h1>
            <p className="mt-1 text-sm text-white/40">MarketWatch AI — Internal</p>
          </div>
          <a href="/dashboard" className="text-sm text-white/50 hover:text-white transition">
            ← Back to Dashboard
          </a>
        </div>

        {/* Stats row */}
        <div className="mb-8 grid gap-4 sm:grid-cols-3">
          <StatCard label="Total Users" value={totalUsers.toString()} />
          <StatCard
            label="Total Revenue"
            value={`₦${totalRevenue.toLocaleString("en-NG", { minimumFractionDigits: 2 })}`}
            accent
          />
          <StatCard
            label="Active Subscriptions"
            value={(subscriptions ?? []).length.toString()}
          />
        </div>

        {/* Tier breakdown */}
        <div className="mb-8 rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="mb-4 text-lg font-semibold">User Tier Breakdown</h2>
          <div className="space-y-3">
            {tiers.map(({ tier, count }) => {
              const pct = totalUsers > 0 ? Math.round((count / totalUsers) * 100) : 0;
              return (
                <div key={tier}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="capitalize text-white/70">{tier}</span>
                    <span className="text-white/50">
                      {count} users ({pct}%)
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
                    <div
                      className={`h-2 rounded-full ${
                        tier === "elite"
                          ? "bg-purple-500"
                          : tier === "pro"
                          ? "bg-emerald-500"
                          : "bg-white/30"
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent subscriptions */}
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="mb-4 text-lg font-semibold">Recent Subscriptions</h2>
          {(subscriptions ?? []).length === 0 ? (
            <p className="text-sm text-white/30">No active subscriptions yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-white/40">
                    <th className="pb-3 pr-6">Plan</th>
                    <th className="pb-3 pr-6">Amount</th>
                    <th className="pb-3 pr-6">Status</th>
                    <th className="pb-3">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {(subscriptions ?? []).slice(0, 20).map((s, i) => (
                    <tr key={i} className="border-b border-white/5">
                      <td className="py-3 pr-6 capitalize text-white/80">{s.plan}</td>
                      <td className="py-3 pr-6 text-emerald-400">
                        ₦{Number(s.amount).toLocaleString()}
                      </td>
                      <td className="py-3 pr-6">
                        <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-400">
                          {s.status}
                        </span>
                      </td>
                      <td className="py-3 text-white/40">
                        {new Date(s.created_at).toLocaleDateString("en-GB")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
      <p className="text-sm text-white/40">{label}</p>
      <p className={`mt-2 text-3xl font-bold ${accent ? "text-emerald-400" : "text-white"}`}>
        {value}
      </p>
    </div>
  );
}
