import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import MobileNav from "@/components/dashboard/MobileNav";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: "📊" },
  { href: "/dashboard/alerts", label: "Alerts", icon: "🔔" },
  { href: "/dashboard/correlation", label: "Correlation", icon: "🔗" },
  { href: "/dashboard/calculator", label: "Calculator", icon: "🧮" },
  { href: "/dashboard/history", label: "History", icon: "📜" },
  { href: "/dashboard/billing", label: "Billing", icon: "💳" },
  { href: "/dashboard/referral", label: "Referral", icon: "🎁" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
];

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("full_name, tier, is_admin")
    .eq("id", session.user.id)
    .maybeSingle();

  const tier = profile?.tier ?? "free";
  const isAdmin = profile?.is_admin === true;

  return (
    <div className="flex min-h-screen bg-black text-white">
      {/* Desktop sidebar */}
      <aside className="hidden w-56 flex-shrink-0 flex-col border-r border-white/10 bg-white/[0.02] px-4 py-8 md:flex">
        <Link href="/" className="mb-8 text-lg font-bold">
          Market<span className="text-emerald-400">Watch</span> AI
        </Link>

        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-white/60 transition hover:bg-white/5 hover:text-white"
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          ))}

          {isAdmin && (
            <Link
              href="/dashboard/admin"
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-white/60 transition hover:bg-white/5 hover:text-white"
            >
              <span>🛡️</span>
              Admin
            </Link>
          )}
        </nav>

        <div className="border-t border-white/10 pt-4">
          <p className="mb-1 truncate text-xs text-white/40">
            {session.user.email}
          </p>
          <span className="inline-block rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs capitalize text-emerald-400">
            {tier}
          </span>

          <form action="/auth/logout" method="POST" className="mt-3">
            <button
              type="submit"
              className="text-xs text-white/30 hover:text-white transition"
            >
              Log out →
            </button>
          </form>
        </div>
      </aside>

      {/* Mobile nav (hamburger + drawer) */}
      <div className="flex flex-1 flex-col md:contents">
        <MobileNav
          email={session.user.email ?? ""}
          tier={tier}
          isAdmin={isAdmin}
        />

        {/* Main content */}
        <main className="flex-1 overflow-auto px-4 py-6 md:px-6 md:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
