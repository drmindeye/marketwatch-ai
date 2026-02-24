import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const PLAN_PRICES: Record<string, number> = {
  pro: 500000,   // ₦5,000 in kobo
  elite: 1500000, // ₦15,000 in kobo
};

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { plan } = await request.json() as { plan: string };

  const amount = PLAN_PRICES[plan];
  if (!amount) {
    return NextResponse.json({ error: "Invalid plan" }, { status: 400 });
  }

  const origin = new URL(request.url).origin;

  const res = await fetch("https://api.paystack.co/transaction/initialize", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.PAYSTACK_SECRET_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: session.user.email,
      amount,
      currency: "NGN",
      metadata: { plan, user_id: session.user.id },
      callback_url: `${origin}/payment/callback`,
    }),
  });

  const json = await res.json() as { status: boolean; data?: { authorization_url: string } };

  if (!json.status || !json.data) {
    return NextResponse.json({ error: "Failed to initialize payment" }, { status: 502 });
  }

  return NextResponse.json({ url: json.data.authorization_url });
}
