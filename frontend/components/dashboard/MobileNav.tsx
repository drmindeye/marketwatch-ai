"use client";

import { useState } from "react";
import Link from "next/link";

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

interface Props {
  email: string;
  tier: string;
  isAdmin: boolean;
}

export default function MobileNav({ email, tier, isAdmin }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Mobile top bar */}
      <div className="flex items-center justify-between border-b border-white/10 bg-black px-4 py-3 md:hidden">
        <Link href="/" className="text-base font-bold">
          Market<span className="text-emerald-400">Watch</span> AI
        </Link>
        <button
          onClick={() => setOpen(true)}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-white/60 hover:text-white"
          aria-label="Open menu"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M2 4h14M2 9h14M2 14h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </button>
      </div>

      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Slide-in drawer */}
      <div
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-white/10 bg-black transition-transform duration-200 md:hidden ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-4 py-4">
          <Link href="/" className="text-base font-bold" onClick={() => setOpen(false)}>
            Market<span className="text-emerald-400">Watch</span> AI
          </Link>
          <button
            onClick={() => setOpen(false)}
            className="text-white/40 hover:text-white"
            aria-label="Close menu"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M3 3l12 12M15 3L3 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        <nav className="flex flex-1 flex-col gap-1 px-3">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 rounded-lg px-3 py-3 text-sm text-white/60 transition hover:bg-white/5 hover:text-white"
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          ))}
          {isAdmin && (
            <Link
              href="/dashboard/admin"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 rounded-lg px-3 py-3 text-sm text-white/60 transition hover:bg-white/5 hover:text-white"
            >
              <span className="text-base">🛡️</span>
              Admin
            </Link>
          )}
        </nav>

        <div className="border-t border-white/10 px-4 py-4">
          <p className="mb-1 truncate text-xs text-white/40">{email}</p>
          <span className="inline-block rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs capitalize text-emerald-400">
            {tier}
          </span>
          <form action="/auth/logout" method="POST" className="mt-3">
            <button type="submit" className="text-xs text-white/30 hover:text-white transition">
              Log out →
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
