"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Header() {
  const [open, setOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-black/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-xl font-bold text-white">
            Market<span className="text-emerald-400">Watch</span> AI
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-8 md:flex">
          <Link href="#features" className="text-sm text-white/70 transition hover:text-white">
            Features
          </Link>
          <Link href="#pricing" className="text-sm text-white/70 transition hover:text-white">
            Pricing
          </Link>
        </nav>

        {/* Desktop CTA */}
        <div className="hidden items-center gap-3 md:flex">
          <Button variant="ghost" className="text-white/80 hover:text-white" asChild>
            <Link href="/login">Log in</Link>
          </Button>
          <Button className="bg-emerald-500 text-black hover:bg-emerald-400" asChild>
            <Link href="/signup">Get Started</Link>
          </Button>
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setOpen(!open)}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-white/60 hover:text-white md:hidden"
          aria-label="Toggle menu"
        >
          {open ? (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M3 3l12 12M15 3L3 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M2 4h14M2 9h14M2 14h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          )}
        </button>
      </div>

      {/* Mobile dropdown menu */}
      {open && (
        <div className="border-t border-white/10 bg-black/95 px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-1 mb-4">
            <Link
              href="#features"
              onClick={() => setOpen(false)}
              className="rounded-lg px-3 py-2.5 text-sm text-white/70 transition hover:bg-white/5 hover:text-white"
            >
              Features
            </Link>
            <Link
              href="#pricing"
              onClick={() => setOpen(false)}
              className="rounded-lg px-3 py-2.5 text-sm text-white/70 transition hover:bg-white/5 hover:text-white"
            >
              Pricing
            </Link>
          </nav>
          <div className="flex flex-col gap-2 border-t border-white/10 pt-4">
            <Button variant="ghost" className="w-full justify-center text-white/80 hover:text-white" asChild>
              <Link href="/login" onClick={() => setOpen(false)}>Log in</Link>
            </Button>
            <Button className="w-full justify-center bg-emerald-500 text-black hover:bg-emerald-400" asChild>
              <Link href="/signup" onClick={() => setOpen(false)}>Get Started</Link>
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}
