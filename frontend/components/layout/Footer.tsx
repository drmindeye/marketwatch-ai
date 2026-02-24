import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-white/10 px-6 py-12">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
          <Link href="/" className="text-lg font-bold text-white">
            Market<span className="text-emerald-400">Watch</span> AI
          </Link>

          <nav className="flex flex-wrap items-center gap-6 text-sm text-white/50">
            <Link href="#features" className="hover:text-white transition">Features</Link>
            <Link href="#pricing" className="hover:text-white transition">Pricing</Link>
            <Link href="/login" className="hover:text-white transition">Login</Link>
            <Link href="/signup" className="hover:text-white transition">Sign Up</Link>
          </nav>

          <p className="text-sm text-white/30">
            &copy; {new Date().getFullYear()} MarketWatch AI. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
