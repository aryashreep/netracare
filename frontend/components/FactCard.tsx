"use client";

import { useEffect, useState } from "react";
import { getFactOfTheDay } from "@/lib/api";

export default function FactCard() {
  const [fact, setFact] = useState<string | null>(null);
  const [caveat, setCaveat] = useState<string>(
    "General information, not medical advice",
  );
  const [busy, setBusy] = useState(false);

  async function load(previous?: string) {
    setBusy(true);
    try {
      const r = await getFactOfTheDay(previous);
      setFact(r.fact);
      setCaveat(r.caveat);
    } catch {
      // Endpoint never 500s — it has its own fallback — but keep belt and
      // braces so a network error doesn't blow up the home screen.
      setFact(
        "Looking at something 20 feet away for 20 seconds every 20 minutes helps rest tired eyes.",
      );
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <section className="mt-6 border border-slate-200 bg-slate-50 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-widest text-clinic-accent">
          Fact of the day
        </p>
        <button
          onClick={() => load(fact || undefined)}
          disabled={busy}
          className="text-sm text-slate-600 border border-slate-300 rounded px-2 py-1 disabled:opacity-50"
        >
          {busy ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <p className="mt-2 text-slate-900 leading-snug">
        {fact ?? "Loading…"}
      </p>
      <p className="mt-2 text-xs text-slate-500 italic">{caveat}</p>
    </section>
  );
}
