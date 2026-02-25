import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? null;

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      // If a specific next is requested, honour it
      if (next) return NextResponse.redirect(`${origin}${next}`);

      // New users (no telegram_id) → onboarding; returning users → dashboard
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        const { data: profile } = await supabase
          .from("profiles")
          .select("telegram_id")
          .eq("id", session.user.id)
          .maybeSingle();
        const dest = profile?.telegram_id ? "/dashboard" : "/onboarding";
        return NextResponse.redirect(`${origin}${dest}`);
      }

      return NextResponse.redirect(`${origin}/dashboard`);
    }
  }

  return NextResponse.redirect(`${origin}/login?message=Could not authenticate`);
}
