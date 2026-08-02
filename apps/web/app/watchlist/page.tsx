"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { ScrollText, X } from "lucide-react";
import { toast } from "sonner";

import { WebSocketStatus } from "@/components/realtime/WebSocketStatus";
import { useRealtimePrices, type AssetType } from "@/hooks/useRealtimePrices";
import { useAppStore } from "@/store/useAppStore";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PriceDelta } from "@/components/ui/PriceDelta";
import { apiFetch } from "@/lib/api";

export default function WatchlistPage() {
  const { watchlistItems, setWatchlistItems } = useAppStore();
  const [watchlistId, setWatchlistId] = useState<number | null>(null);
  const [symbolInput, setSymbolInput] = useState("");
  const [assetTypeInput, setAssetTypeInput] = useState<AssetType>("stock");
  const [submitting, setSubmitting] = useState(false);
  const [loaded, setLoaded] = useState(false);

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
        const resp = await apiFetch("/api/v1/watchlists/default");
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
      } finally {
        setLoaded(true);
      }
    }

    loadWatchlist();
  }, [setWatchlistItems]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    const trimmed = symbolInput.trim().toUpperCase();
    if (!trimmed || submitting) return;
    setSubmitting(true);
    try {
      let targetId = watchlistId;
      if (targetId == null) {
        const defaultResp = await apiFetch("/api/v1/watchlists/default");
        if (!defaultResp.ok) throw new Error("Could not reach the watchlist API.");
        targetId = (await defaultResp.json()).id;
        setWatchlistId(targetId);
      }
      const resp = await apiFetch(`/api/v1/watchlists/${targetId}/items`, {
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
        toast.success(`${trimmed} added to watchlist`);
      } else {
        const body = await resp.json().catch(() => null);
        toast.error(body?.message ?? `Could not add ${trimmed}.`);
      }
    } catch {
      toast.error("Could not reach the API. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(itemId: number, symbol: string) {
    if (watchlistId == null) return;
    try {
      const resp = await apiFetch(`/api/v1/watchlists/${watchlistId}/items/${itemId}`, {
        method: "DELETE"
      });
      if (resp.ok) {
        setWatchlistItems(watchlistItems.filter((w) => w.id !== itemId));
        toast(`${symbol} removed`);
      }
    } catch {
      toast.error("Could not remove symbol. Please try again.");
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">Watchlist</h1>
          <p className="text-sm text-muted">Track your favorite symbols and see live price updates.</p>
        </div>
        <WebSocketStatus status={status} />
      </div>

      <Card className="p-4">
        <form onSubmit={handleAdd} className="flex flex-wrap gap-2">
          <Input
            type="text"
            placeholder={assetTypeInput === "crypto" ? "Symbol (e.g. BTC, ETH)" : "Symbol (e.g. AAPL, MSFT)"}
            value={symbolInput}
            onChange={(e) => setSymbolInput(e.target.value)}
            className="min-w-[160px] flex-1"
          />
          <Select
            value={assetTypeInput}
            onChange={(e) => setAssetTypeInput(e.target.value as AssetType)}
            aria-label="Asset type"
          >
            <option value="stock">Stock</option>
            <option value="crypto">Crypto</option>
          </Select>
          <Button type="submit" disabled={submitting || !symbolInput.trim()}>
            {submitting ? "Adding…" : "Add"}
          </Button>
        </form>
      </Card>

      <Card className="overflow-hidden p-0">
        {loaded && watchlistItems.length === 0 ? (
          <EmptyState
            icon={<ScrollText className="h-5 w-5" />}
            title="Your watchlist is empty"
            description="Add a symbol above to start tracking live prices."
            className="border-none"
          />
        ) : (
          <table className="min-w-full divide-y text-sm">
            <thead className="bg-surface-hover/40">
              <tr>
                <th scope="col" className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted">
                  Symbol
                </th>
                <th scope="col" className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted">
                  Type
                </th>
                <th scope="col" className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted">
                  Last Price
                </th>
                <th scope="col" className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted">
                  24h Change
                </th>
                <th scope="col" className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y">
              <AnimatePresence initial={false}>
                {watchlistItems.map((item) => {
                  const tick = ticks[item.symbol];
                  return (
                    <motion.tr
                      key={item.id}
                      layout
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                      className="group hover:bg-surface-hover/60"
                    >
                      <td className="px-4 py-2.5 font-medium">
                        <Link
                          href={`/symbol/${item.symbol}?asset_type=${item.assetType}`}
                          className="text-foreground hover:text-brand-light"
                        >
                          {item.symbol}
                        </Link>
                      </td>
                      <td className="px-4 py-2.5 text-xs uppercase text-muted">{item.assetType}</td>
                      <td className="px-4 py-2.5 tabular-nums text-foreground">
                        {tick ? `$${tick.price.toFixed(2)}` : <span className="text-muted">—</span>}
                      </td>
                      <td className="px-4 py-2.5">
                        <PriceDelta value={tick?.change24h} />
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <button
                          type="button"
                          onClick={() => handleRemove(item.id, item.symbol)}
                          aria-label={`Remove ${item.symbol}`}
                          className="rounded-md p-1 text-muted opacity-0 transition-opacity hover:text-negative group-hover:opacity-100"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </motion.tr>
                  );
                })}
              </AnimatePresence>
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
