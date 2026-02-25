import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL!;

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? null;
  const ref = searchParams.get("ref") ?? null;

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      // If a specific next is requested, honour it
      if (next) return NextResponse.redirect(`${origin}${next}`);

      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        // Claim referral if a ref code was passed through signup
        if (ref) {
          try {
            await fetch(`${BACKEND}/api/referral/claim`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${session.access_token}`,
              },
              body: JSON.stringify({ code: ref }),
            });
          } catch {
            // Non-fatal — don't block login on referral failure
          }
        }

        // New users (no telegram_id) → onboarding; returning users → dashboard
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
