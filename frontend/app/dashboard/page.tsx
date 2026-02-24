import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("full_name, tier")
    .eq("id", session.user.id)
    .single();

  return (
    <div className="min-h-screen bg-black px-6 py-12 text-white">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              Welcome, {profile?.full_name ?? session.user.email}
            </h1>
            <p className="mt-1 text-sm capitalize text-white/50">
              Plan: <span className="text-emerald-400">{profile?.tier ?? "free"}</span>
            </p>
          </div>

          <form action="/auth/logout" method="POST">
            <button
              type="submit"
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-white/70 transition hover:bg-white/5 hover:text-white"
            >
              Log out
            </button>
          </form>
        </div>

        <p className="text-white/40">
          Dashboard coming in Phase 3. Alerts, AI summaries, and trade tools will live here.
        </p>
      </div>
    </div>
  );
}
