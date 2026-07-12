"use client";

import { FormEvent, useEffect, useState } from "react";

interface AlertRow {
  id: number;
  symbol: string;
  asset_type: string;
  direction: string;
  threshold: number;
  is_active: boolean;
  created_at: string;
}

const DIRECTION_LABELS: Record<string, string> = {
  price_above: "Price above",
  price_below: "Price below",
  rsi_above: "RSI above",
  rsi_below: "RSI below",
  ma_cross: "MA cross"
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [symbol, setSymbol] = useState("");
  const [assetType, setAssetType] = useState<"stock" | "crypto">("stock");
  const [direction, setDirection] = useState<"price_above" | "price_below">("price_above");
  const [threshold, setThreshold] = useState("");

  useEffect(() => {
    async function loadAlerts() {
      try {
        const apiBase =
          process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
        const resp = await fetch(`${apiBase}/api/v1/alerts`);
        if (!resp.ok) return;
        const data = await resp.json();
        setAlerts(data);
      } catch {
        // ignore for now
      }
    }
    loadAlerts();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!symbol.trim() || !threshold) return;
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
      const resp = await fetch(`${apiBase}/api/v1/alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: symbol.trim().toUpperCase(),
          asset_type: assetType,
          direction,
          threshold: parseFloat(threshold)
        })
      });
      if (resp.ok) {
        const created = await resp.json();
        setAlerts([created, ...alerts]);
        setSymbol("");
        setThreshold("");
      }
    } catch {
      // ignore
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Price Alerts</h1>
        <p className="text-sm text-slate-400">
          Define basic price-above/price-below alerts for your symbols.
        </p>
      </div>

      <form
        onSubmit={handleCreate}
        className="flex flex-wrap gap-3 rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm"
      >
        <input
          type="text"
          placeholder="Symbol (e.g. AAPL)"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="min-w-[120px] flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-brand-light"
        />
        <select
          value={assetType}
          onChange={(e) => setAssetType(e.target.value as "stock" | "crypto")}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-brand-light"
          aria-label="Asset type"
        >
          <option value="stock">Stock</option>
          <option value="crypto">Crypto</option>
        </select>
        <select
          value={direction}
          onChange={(e) => setDirection(e.target.value as any)}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-brand-light"
        >
          <option value="price_above">Price above</option>
          <option value="price_below">Price below</option>
        </select>
        <input
          type="number"
          placeholder="Threshold"
          value={threshold}
          onChange={(e) => setThreshold(e.target.value)}
          className="w-32 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-brand-light"
        />
        <button
          type="submit"
          className="rounded-md bg-brand px-4 py-2 font-medium text-slate-50 hover:bg-brand-light"
        >
          Create alert
        </button>
      </form>

      <div className="rounded-lg border border-slate-800 bg-slate-900/60">
        <table className="min-w-full text-sm">
          <thead className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th className="px-3 py-2 text-left">Symbol</th>
              <th className="px-3 py-2 text-left">Type</th>
              <th className="px-3 py-2 text-left">Condition</th>
              <th className="px-3 py-2 text-right">Threshold</th>
              <th className="px-3 py-2 text-center">Active</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-900/60">
            {alerts.map((a) => (
              <tr key={a.id}>
                <td className="px-3 py-2 text-slate-100">{a.symbol}</td>
                <td className="px-3 py-2 text-xs uppercase text-slate-400">{a.asset_type}</td>
                <td className="px-3 py-2 text-slate-300">
                  {DIRECTION_LABELS[a.direction] ?? a.direction}
                </td>
                <td className="px-3 py-2 text-right">${a.threshold.toFixed(2)}</td>
                <td className="px-3 py-2 text-center text-xs">
                  {a.is_active ? (
                    <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-emerald-400">
                      Active
                    </span>
                  ) : (
                    <span className="rounded-full bg-slate-700/40 px-2 py-0.5 text-slate-400">
                      Inactive
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {alerts.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-3 py-4 text-center text-sm text-slate-500"
                >
                  No alerts yet. Create one above to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}