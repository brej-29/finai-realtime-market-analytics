"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import Link from "next/link";

import { WebSocketStatus } from "../../components/realtime/WebSocketStatus";
import { useRealtimePrices, type AssetType } from "../../hooks/useRealtimePrices";
import { useAppStore } from "../../store/useAppStore";

function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
}

export default function WatchlistPage() {
  const { watchlistItems, setWatchlistItems } = useAppStore();
  const [watchlistId, setWatchlistId] = useState<number | null>(null);
  const [symbolInput, setSymbolInput] = useState("");
  const [assetTypeInput, setAssetTypeInput] = useState<AssetType>("stock");

  const stockSymbols = useMemo(
    () => watchlistItems.filter((w) => w.assetType !== "crypto").map((w) => w.symbol),
    [watchlistItems]
  );
  const cryptoSymbols = useMemo(
    () => watchlistItems.filter((w) => w.assetType === "crypto").map((w) => w.symbol),
    [watchlistItems]
  );

  const stocks = useRealtimePrices({ symbols: stockSymbols, assetType: "stock" });
  const cryptos = useRealtimePrices({ symbols: cryptoSymbols, assetType: "crypto" });

  const ticks = useMemo(() => ({ ...stocks.ticks, ...cryptos.ticks }), [stocks.ticks, cryptos.ticks]);
  const status =
    stocks.status === "connected" || cryptos.status === "connected"
      ? "connected"
      : stocks.status === "connecting" || cryptos.status === "connecting"
        ? "connecting"
        : "disconnected";

  useEffect(() => {
    async function loadWatchlist() {
      try {
        // Get-or-create the shared default watchlist.
        const resp = await fetch(`${getApiBase()}/api/v1/watchlists/default`);
        if (!resp.ok) return;
        const data = await resp.json();
        setWatchlistId(data.id);
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
      const apiBase = getApiBase();
      let targetId = watchlistId;
      if (targetId == null) {
        const defaultResp = await fetch(`${apiBase}/api/v1/watchlists/default`);
        if (!defaultResp.ok) return;
        targetId = (await defaultResp.json()).id;
        setWatchlistId(targetId);
      }
      const resp = await fetch(`${apiBase}/api/v1/watchlists/${targetId}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: trimmed, asset_type: assetTypeInput })
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

  async function handleRemove(itemId: number) {
    if (watchlistId == null) return;
    try {
      const resp = await fetch(
        `${getApiBase()}/api/v1/watchlists/${watchlistId}/items/${itemId}`,
        { method: "DELETE" }
      );
      if (resp.ok) {
        setWatchlistItems(watchlistItems.filter((w) => w.id !== itemId));
      }
    } catch {
      // ignore
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
          placeholder={assetTypeInput === "crypto" ? "Symbol (e.g. BTC, ETH)" : "Symbol (e.g. AAPL, MSFT)"}
          value={symbolInput}
          onChange={(e) => setSymbolInput(e.target.value)}
          className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-brand-light"
        />
        <select
          value={assetTypeInput}
          onChange={(e) => setAssetTypeInput(e.target.value as AssetType)}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-brand-light"
          aria-label="Asset type"
        >
          <option value="stock">Stock</option>
          <option value="crypto">Crypto</option>
        </select>
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
                Type
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                Last Price
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                24h Change
              </th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {watchlistItems.map((item) => {
              const tick = ticks[item.symbol];
              return (
                <tr key={item.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-2 font-medium">
                    <Link
                      href={`/symbol/${item.symbol}?asset_type=${item.assetType}`}
                      className="text-slate-200 hover:text-brand-light"
                    >
                      {item.symbol}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-xs uppercase text-slate-400">
                    {item.assetType}
                  </td>
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
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => handleRemove(item.id)}
                      className="text-xs text-slate-500 hover:text-red-400"
                      aria-label={`Remove ${item.symbol}`}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              );
            })}
            {watchlistItems.length === 0 && (
              <tr>
                <td
                  colSpan={5}
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
