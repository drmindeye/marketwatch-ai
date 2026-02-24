import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-black/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-xl font-bold text-white">
            Market<span className="text-emerald-400">Watch</span> AI
          </span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          <Link href="#features" className="text-sm text-white/70 transition hover:text-white">
            Features
          </Link>
          <Link href="#pricing" className="text-sm text-white/70 transition hover:text-white">
            Pricing
          </Link>
        </nav>

        <div className="flex items-center gap-3">
          <Button variant="ghost" className="text-white/80 hover:text-white" asChild>
            <Link href="/login">Log in</Link>
          </Button>
          <Button className="bg-emerald-500 text-black hover:bg-emerald-400" asChild>
            <Link href="/signup">Get Started</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
