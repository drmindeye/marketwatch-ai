import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function Hero() {
  return (
    <section className="flex min-h-screen flex-col items-center justify-center px-6 pt-16 text-center">
      <Badge className="mb-6 border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
        AI-Powered Forex &amp; Crypto Alerts
      </Badge>

      <h1 className="max-w-4xl text-5xl font-bold leading-tight tracking-tight text-white md:text-7xl">
        Never Miss a{" "}
        <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
          Market Move
        </span>{" "}
        Again
      </h1>

      <p className="mt-6 max-w-2xl text-lg text-white/60">
        Set price alerts on Forex, crypto, and stocks. Get notified instantly on
        WhatsApp and Telegram. Powered by Claude AI for market insights.
      </p>

      <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
        <Button size="lg" className="bg-emerald-500 text-black hover:bg-emerald-400 px-8" asChild>
          <Link href="/signup">Start Free</Link>
        </Button>
        <Button size="lg" variant="outline" className="border-white/20 text-white hover:bg-white/10" asChild>
          <Link href="#features">See How It Works</Link>
        </Button>
      </div>

      <div className="mt-16 flex flex-wrap items-center justify-center gap-8 text-sm text-white/40">
        <span>✓ No credit card required</span>
        <span>✓ Free Telegram alerts</span>
        <span>✓ Set up in 2 minutes</span>
      </div>
    </section>
  );
}
