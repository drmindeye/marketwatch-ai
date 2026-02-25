import { redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

export default async function OnboardingPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("telegram_id, full_name")
    .eq("id", session.user.id)
    .maybeSingle();

  // Already linked — skip onboarding
  if (profile?.telegram_id) redirect("/dashboard");

  const name = profile?.full_name?.split(" ")[0] || "there";

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-black px-6 py-12 text-white">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="mb-10 text-center">
          <Link href="/" className="mb-6 inline-block text-xl font-bold">
            Market<span className="text-emerald-400">Watch</span> AI
          </Link>
          <h1 className="mt-4 text-3xl font-bold">Hey {name}, one last step.</h1>
          <p className="mt-3 text-white/50">
            Link your Telegram to start receiving price alerts.
          </p>
        </div>

        {/* Steps */}
        <div className="space-y-4">
          <Step
            number={1}
            title="Open the MarketWatch AI bot"
            description={
              <>
                Tap the link below to open{" "}
                <a
                  href="https://t.me/marketwatchai_bot"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-emerald-400 underline-offset-4 hover:underline"
                >
                  @marketwatchai_bot
                </a>{" "}
                in Telegram and press <strong>Start</strong>.
              </>
            }
          />

          <Step
            number={2}
            title="Send the link command"
            description={
              <>
                In the bot chat, type exactly:
                <code className="mt-2 block rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 font-mono text-sm text-emerald-300">
                  /link {session.user.email}
                </code>
              </>
            }
          />

          <Step
            number={3}
            title="You're linked!"
            description="The bot will confirm instantly. Your account is now connected — alerts, AI chat, and calculators are all ready."
          />
        </div>

        {/* CTA */}
        <a
          href="https://t.me/marketwatchai_bot"
          target="_blank"
          rel="noopener noreferrer"
          className="mt-8 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 font-semibold text-black transition hover:bg-emerald-400"
        >
          Open Telegram Bot →
        </a>

        <Link
          href="/dashboard"
          className="mt-4 block text-center text-sm text-white/30 transition hover:text-white/60"
        >
          Skip for now — I&apos;ll link later
        </Link>
      </div>
    </main>
  );
}

function Step({
  number,
  title,
  description,
}: {
  number: number;
  title: string;
  description: React.ReactNode;
}) {
  return (
    <div className="flex gap-4 rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-sm font-bold text-emerald-400">
        {number}
      </div>
      <div>
        <p className="font-semibold text-white">{title}</p>
        <div className="mt-1 text-sm text-white/55">{description}</div>
      </div>
    </div>
  );
}
