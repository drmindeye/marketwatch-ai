"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL;

type Tab = "rr" | "position" | "pips";

export default function CalculatorPage() {
  const [tab, setTab] = useState<Tab>("rr");

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Trade Calculator</h1>
        <p className="mt-1 text-sm text-white/40">
          Know your numbers before entering a trade.
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
        {(["rr", "position", "pips"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
              tab === t
                ? "bg-emerald-500 text-black"
                : "text-white/50 hover:text-white"
            }`}
          >
            {t === "rr" ? "Risk / Reward" : t === "position" ? "Position Size" : "Pip Value"}
          </button>
        ))}
      </div>

      {tab === "rr" && <RRCalculator />}
      {tab === "position" && <PositionCalculator />}
      {tab === "pips" && <PipCalculator />}
    </div>
  );
}

// ── Risk/Reward ────────────────────────────────────────────────
function RRCalculator() {
  const [entry, setEntry] = useState("");
  const [sl, setSl] = useState("");
  const [tp, setTp] = useState("");
  const [result, setResult] = useState<{ risk_pips: number; reward_pips: number; ratio: number; ratio_label: string } | null>(null);
  const [loading, setLoading] = useState(false);

  async function calculate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const res = await fetch(`${BACKEND}/api/trade/risk-reward`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entry: +entry, stop_loss: +sl, take_profit: +tp }),
    });
    if (res.ok) setResult(await res.json());
    setLoading(false);
  }

  return (
    <form onSubmit={calculate} className="space-y-4">
      <Field label="Entry Price" value={entry} onChange={setEntry} placeholder="1.10000" />
      <Field label="Stop Loss" value={sl} onChange={setSl} placeholder="1.09500" />
      <Field label="Take Profit" value={tp} onChange={setTp} placeholder="1.11000" />
      <Button type="submit" disabled={loading} className="w-full bg-emerald-500 text-black hover:bg-emerald-400">
        {loading ? "Calculating..." : "Calculate"}
      </Button>
      {result && (
        <ResultBox>
          <ResultRow label="Risk" value={`${result.risk_pips} pips`} />
          <ResultRow label="Reward" value={`${result.reward_pips} pips`} />
          <ResultRow label="R/R Ratio" value={result.ratio_label} accent />
        </ResultBox>
      )}
    </form>
  );
}

// ── Position Size ─────────────────────────────────────────────
function PositionCalculator() {
  const [balance, setBalance] = useState("");
  const [risk, setRisk] = useState("1");
  const [slPips, setSlPips] = useState("");
  const [pipValue, setPipValue] = useState("10");
  const [result, setResult] = useState<{ risk_amount: number; lots: number; units: number } | null>(null);
  const [loading, setLoading] = useState(false);

  async function calculate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const res = await fetch(`${BACKEND}/api/trade/position-size`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_balance: +balance,
        risk_percent: +risk,
        stop_loss_pips: +slPips,
        pip_value: +pipValue,
      }),
    });
    if (res.ok) setResult(await res.json());
    setLoading(false);
  }

  return (
    <form onSubmit={calculate} className="space-y-4">
      <Field label="Account Balance ($)" value={balance} onChange={setBalance} placeholder="10000" />
      <Field label="Risk %" value={risk} onChange={setRisk} placeholder="1" />
      <Field label="Stop Loss (pips)" value={slPips} onChange={setSlPips} placeholder="50" />
      <Field label="Pip Value per Lot ($)" value={pipValue} onChange={setPipValue} placeholder="10" />
      <Button type="submit" disabled={loading} className="w-full bg-emerald-500 text-black hover:bg-emerald-400">
        {loading ? "Calculating..." : "Calculate"}
      </Button>
      {result && (
        <ResultBox>
          <ResultRow label="Risk Amount" value={`$${result.risk_amount}`} />
          <ResultRow label="Position Size" value={`${result.lots} lots`} accent />
          <ResultRow label="Units" value={result.units.toLocaleString()} />
        </ResultBox>
      )}
    </form>
  );
}

// ── Pip Calculator ────────────────────────────────────────────
function PipCalculator() {
  const [symbol, setSymbol] = useState("EURUSD");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [result, setResult] = useState<{ pips: number; direction: string } | null>(null);
  const [loading, setLoading] = useState(false);

  async function calculate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const res = await fetch(`${BACKEND}/api/trade/pips`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, price_from: +from, price_to: +to }),
    });
    if (res.ok) setResult(await res.json());
    setLoading(false);
  }

  return (
    <form onSubmit={calculate} className="space-y-4">
      <div>
        <label className="mb-1.5 block text-xs text-white/50">Symbol</label>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
          placeholder="EURUSD"
        />
      </div>
      <Field label="Price From" value={from} onChange={setFrom} placeholder="1.10000" />
      <Field label="Price To" value={to} onChange={setTo} placeholder="1.10500" />
      <Button type="submit" disabled={loading} className="w-full bg-emerald-500 text-black hover:bg-emerald-400">
        {loading ? "Calculating..." : "Calculate"}
      </Button>
      {result && (
        <ResultBox>
          <ResultRow label="Pips" value={`${result.pips} pips`} accent />
          <ResultRow label="Direction" value={result.direction === "up" ? "▲ Up" : "▼ Down"} />
        </ResultBox>
      )}
    </form>
  );
}

// ── Shared UI ─────────────────────────────────────────────────
function Field({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <div>
      <label className="mb-1.5 block text-xs text-white/50">{label}</label>
      <input
        type="number"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required
        className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500"
      />
    </div>
  );
}

function ResultBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 space-y-2">
      {children}
    </div>
  );
}

function ResultRow({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-white/50">{label}</span>
      <span className={accent ? "font-bold text-emerald-400" : "text-white"}>{value}</span>
    </div>
  );
}
