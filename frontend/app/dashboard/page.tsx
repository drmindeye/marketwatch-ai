import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

const CARDS = [
  {
    href: "/dashboard/alerts",
    icon: "🔔",
    title: "Price Alerts",
    description: "Set Touch, Cross, or Near Level alerts on any Forex pair, crypto, or stock.",
    cta: "Manage Alerts",
  },
  {
    href: "/dashboard/calculator",
    icon: "🧮",
    title: "Trade Calculator",
    description: "Calculate Risk/Reward, position size, and pips before you enter a trade.",
    cta: "Open Calculator",
  },
];

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("full_name, tier")
    .eq("id", session.user.id)
    .single();

  const { count: activeAlerts } = await supabase
    .from("alerts")
    .select("id", { count: "exact", head: true })
    .eq("user_id", session.user.id)
    .eq("is_active", true);

  const { count: triggered } = await supabase
    .from("alerts")
    .select("id", { count: "exact", head: true })
    .eq("user_id", session.user.id)
    .not("triggered_at", "is", null);

  return (
    <div className="max-w-4xl">
      {/* Header */}
      <div className="mb-10">
        <h1 className="text-2xl font-bold">
          Welcome back, {profile?.full_name?.split(" ")[0] ?? "Trader"} 👋
        </h1>
        <p className="mt-1 text-sm text-white/40">
          Here&apos;s what&apos;s happening with your account.
        </p>
      </div>

      {/* Stats */}
      <div className="mb-10 grid gap-4 sm:grid-cols-3">
        <StatCard label="Active Alerts" value={String(activeAlerts ?? 0)} />
        <StatCard label="Alerts Triggered" value={String(triggered ?? 0)} accent />
        <StatCard label="Plan" value={profile?.tier ?? "free"} capitalize />
      </div>

      {/* Feature cards */}
      <div className="grid gap-6 sm:grid-cols-2">
        {CARDS.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="group flex flex-col rounded-2xl border border-white/10 bg-white/5 p-6 transition hover:border-emerald-500/30 hover:bg-white/8"
          >
            <span className="mb-4 text-3xl">{card.icon}</span>
            <h3 className="text-lg font-semibold text-white">{card.title}</h3>
            <p className="mt-2 flex-1 text-sm text-white/50">{card.description}</p>
            <span className="mt-6 text-sm font-medium text-emerald-400 transition group-hover:underline">
              {card.cta} →
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent = false,
  capitalize = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
  capitalize?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <p className="text-xs text-white/40">{label}</p>
      <p className={`mt-2 text-2xl font-bold ${accent ? "text-emerald-400" : "text-white"} ${capitalize ? "capitalize" : ""}`}>
        {value}
      </p>
    </div>
  );
}
