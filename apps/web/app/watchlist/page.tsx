"use client";

import { FormEvent, useEffect, useState } from "react";

import { WebSocketStatus } from "../../components/realtime/WebSocketStatus";
import { useRealtimePrices } from "../../hooks/useRealtimePrices";
import { useAppStore } from "../../store/useAppStore";

export default function WatchlistPage() {
  const { watchlistItems, setWatchlistItems } = useAppStore();
  const [symbolInput, setSymbolInput] = useState("");
  const symbols = watchlistItems.map((w) => w.symbol);
  const { status, ticks } = useRealtimePrices({ symbols, assetType: "stock" });

  useEffect(() => {
    async function loadWatchlist() {
      try {
        const apiBase =
          process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
        // For MVP we assume a single default watchlist with ID=1 if it exists
        const resp = await fetch(`${apiBase}/api/v1/watchlists/1`);
        if (!resp.ok) return;
        const data = await resp.json();
        const items =
          data.items?.map((item: any) => ({
            id: item.id,
            symbol: item.symbol,
            assetType: item.asset_type
          })) ?? [];
        setWatchlistItems(items);
      } catch {
        // ignore; empty watchlist is fine
      }
    }

    loadWatchlist();
  }, [setWatchlistItems]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    const trimmed = symbolInput.trim().toUpperCase();
    if (!trimmed) return;
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
      // Create default watchlist if needed
      const createResp = await fetch(`${apiBase}/api/v1/watchlists`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "Default" })
      });
      const created = await createResp.json();
      const watchlistId = created.id;
      const resp = await fetch(`${apiBase}/api/v1/watchlists/${watchlistId}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: trimmed, asset_type: "stock" })
      });
      if (resp.ok) {
        const item = await resp.json();
        setWatchlistItems([
          ...watchlistItems,
          { id: item.id, symbol: item.symbol, assetType: item.asset_type }
        ]);
        setSymbolInput("");
      }
    } catch {
      // ignore errors for now; UI remains optimistic
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Watchlist</h1>
          <p className="text-sm text-slate-400">
            Track your favorite symbols and see live price updates.
          </p>
        </div>
        <WebSocketStatus status={status} />
      </div>

      <form onSubmit={handleAdd} className="flex flex-wrap gap-2">
        <input
          type="text"
          placeholder="Symbol (e.g. AAPL, MSFT)"
          value={symbolInput}
          onChange={(e) => setSymbolInput(e.target.value)}
          className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-brand-light"
        />
        <button
          type="submit"
          className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-slate-50 hover:bg-brand-light"
        >
          Add
        </button>
      </form>

      <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900/60">
        <table className="min-w-full divide-y divide-slate-800 text-sm">
          <thead className="bg-slate-900/80">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                Symbol
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                Last Price
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                24h Change
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {watchlistItems.map((item) => {
              const tick = ticks[item.symbol];
              return (
                <tr key={item.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-2 font-medium text-slate-200">{item.symbol}</td>
                  <td className="px-4 py-2 text-slate-100">
                    {tick ? `$${tick.price.toFixed(2)}` : <span className="text-slate-500">—</span>}
                  </td>
                  <td className="px-4 py-2">
                    {tick && typeof tick.change24h === "number" ? (
                      <span
                        className={
                          tick.change24h >= 0 ? "text-emerald-400 text-xs" : "text-red-400 text-xs"
                        }
                      >
                        {tick.change24h.toFixed(2)}%
                      </span>
                    ) : (
                      <span className="text-xs text-slate-500">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
            {watchlistItems.length === 0 && (
              <tr>
                <td
                  colSpan={3}
                  className="px-4 py-6 text-center text-sm text-slate-500"
                >
                  No symbols yet. Add one above to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}