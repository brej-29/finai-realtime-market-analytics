"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AnimatePresence, motion } from "motion/react";
import { Wallet, X } from "lucide-react";
import { toast } from "sonner";

import { DonutChart } from "@/components/charts/DonutChart";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { PriceDelta } from "@/components/ui/PriceDelta";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatCurrency } from "@/lib/utils";

interface HoldingRow {
  id: number;
  symbol: string;
  asset_type: "stock" | "crypto";
  quantity: number;
  average_price: number;
  created_at: string;
}

interface Quote {
  symbol: string;
  asset_type: string;
  price: number;
}

const SLICE_COLORS = ["#14B8A6", "#818CF8", "#F97316", "#38BDF8", "#F472B6", "#A3E635"];

function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
}

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<HoldingRow[]>([]);
  const [prices, setPrices] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [symbolInput, setSymbolInput] = useState("");
  const [assetTypeInput, setAssetTypeInput] = useState<"stock" | "crypto">("stock");
  const [quantityInput, setQuantityInput] = useState("");
  const [avgPriceInput, setAvgPriceInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [removingId, setRemovingId] = useState<number | null>(null);

  async function loadHoldings() {
    try {
      const apiBase = getApiBase();
      const resp = await fetch(`${apiBase}/api/v1/holdings`);
      if (!resp.ok) return;
      const data: HoldingRow[] = await resp.json();
      setHoldings(data);

      const byType = new Map<string, string[]>();
      for (const h of data) {
        byType.set(h.asset_type, [...(byType.get(h.asset_type) ?? []), h.symbol]);
      }
      const priceMap: Record<string, number> = {};
      await Promise.all(
        Array.from(byType.entries()).map(async ([assetType, symbols]) => {
          const params = new URLSearchParams({ asset_type: assetType });
          symbols.forEach((s) => params.append("symbols", s));
          const qResp = await fetch(`${apiBase}/api/v1/quotes?${params.toString()}`);
          if (!qResp.ok) return;
          const qData = await qResp.json();
          for (const q of (qData.quotes ?? []) as Quote[]) {
            priceMap[`${q.asset_type}:${q.symbol}`] = q.price;
          }
        })
      );
      setPrices(priceMap);
    } catch {
      // ignore for now
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHoldings();
  }, []);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    const trimmed = symbolInput.trim().toUpperCase();
    const quantity = parseFloat(quantityInput);
    const averagePrice = parseFloat(avgPriceInput);
    if (!trimmed || !(quantity > 0) || !(averagePrice >= 0) || submitting) return;
    setSubmitting(true);
    try {
      const resp = await fetch(`${getApiBase()}/api/v1/holdings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: trimmed,
          asset_type: assetTypeInput,
          quantity,
          average_price: averagePrice
        })
      });
      if (resp.ok) {
        setSymbolInput("");
        setQuantityInput("");
        setAvgPriceInput("");
        toast.success(`${trimmed} added to portfolio`);
        setLoading(true);
        await loadHoldings();
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

  async function handleRemove(holdingId: number, symbol: string) {
    setRemovingId(holdingId);
    try {
      const resp = await fetch(`${getApiBase()}/api/v1/holdings/${holdingId}`, {
        method: "DELETE"
      });
      if (resp.ok) {
        setHoldings((prev) => prev.filter((h) => h.id !== holdingId));
        toast(`${symbol} removed`);
      } else {
        toast.error(`Could not remove ${symbol}. Please try again.`);
      }
    } catch {
      toast.error("Could not reach the API. Please try again.");
    } finally {
      setRemovingId(null);
    }
  }

  const rows = useMemo(
    () =>
      holdings.map((h) => {
        const livePrice = prices[`${h.asset_type}:${h.symbol}`] ?? h.average_price;
        const costBasis = h.quantity * h.average_price;
        const marketValue = h.quantity * livePrice;
        return {
          ...h,
          livePrice,
          costBasis,
          marketValue,
          pnl: marketValue - costBasis,
          pnlPct: costBasis > 0 ? ((marketValue - costBasis) / costBasis) * 100 : 0
        };
      }),
    [holdings, prices]
  );

  const slices = useMemo(
    () =>
      rows.map((r, i) => ({
        label: r.symbol,
        value: r.marketValue,
        color: SLICE_COLORS[i % SLICE_COLORS.length]
      })),
    [rows]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-5xl space-y-6"
    >
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">Portfolio</h1>
        <p className="text-sm text-muted">Track your holdings and see your allocation at a glance.</p>
      </div>

      <Card className="p-4">
        <form onSubmit={handleAdd} className="flex flex-wrap gap-2.5">
          <Input
            type="text"
            placeholder={assetTypeInput === "crypto" ? "Symbol (e.g. BTC, ETH)" : "Symbol (e.g. AAPL, MSFT)"}
            value={symbolInput}
            onChange={(e) => setSymbolInput(e.target.value)}
            className="min-w-[140px] flex-1"
          />
          <Select
            value={assetTypeInput}
            onChange={(e) => setAssetTypeInput(e.target.value as "stock" | "crypto")}
            aria-label="Asset type"
          >
            <option value="stock">Stock</option>
            <option value="crypto">Crypto</option>
          </Select>
          <Input
            type="number"
            placeholder="Quantity"
            min="0"
            step="any"
            value={quantityInput}
            onChange={(e) => setQuantityInput(e.target.value)}
            className="w-28"
          />
          <Input
            type="number"
            placeholder="Avg price"
            min="0"
            step="any"
            value={avgPriceInput}
            onChange={(e) => setAvgPriceInput(e.target.value)}
            className="w-28"
          />
          <Button
            type="submit"
            disabled={submitting || !symbolInput.trim() || !quantityInput || !avgPriceInput}
          >
            {submitting ? "Adding…" : "Add holding"}
          </Button>
        </form>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="overflow-hidden p-0 md:col-span-2">
          <div className="border-b px-4 py-3 sm:px-5">
            <h2 className="text-sm font-semibold text-foreground">Holdings</h2>
          </div>
          {loading ? (
            <div className="space-y-3 p-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : rows.length === 0 ? (
            <EmptyState
              icon={<Wallet className="h-5 w-5" />}
              title="No holdings yet"
              description="Holdings are seeded via the demo dataset or added through the API."
              className="border-none"
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y text-sm">
                <thead className="bg-surface-hover/40">
                  <tr>
                    <th scope="col" className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted">
                      Symbol
                    </th>
                    <th scope="col" className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-muted">
                      Qty
                    </th>
                    <th scope="col" className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-muted">
                      Avg Price
                    </th>
                    <th scope="col" className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-muted">
                      Market Value
                    </th>
                    <th scope="col" className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-muted">
                      P&amp;L
                    </th>
                    <th scope="col" className="px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  <AnimatePresence initial={false}>
                    {rows.map((r) => (
                      <motion.tr
                        key={r.id}
                        layout
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="group hover:bg-surface-hover/60"
                      >
                        <td className="px-4 py-2.5 font-medium text-foreground">
                          {r.symbol}
                          <span className="ml-1.5 text-[10px] uppercase text-muted">{r.asset_type}</span>
                        </td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-muted">{r.quantity}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-muted">
                          {formatCurrency(r.average_price)}
                        </td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-foreground">
                          {formatCurrency(r.marketValue)}
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <PriceDelta value={r.pnlPct} />
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <button
                            type="button"
                            onClick={() => handleRemove(r.id, r.symbol)}
                            disabled={removingId === r.id}
                            aria-label={`Remove ${r.symbol}`}
                            className="rounded-md p-1 text-muted opacity-0 transition-opacity hover:text-negative group-hover:opacity-100 disabled:pointer-events-none disabled:opacity-50"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card>
          <CardContent className="pt-5">
            <h2 className="mb-3 text-sm font-semibold text-foreground">Allocation</h2>
            {loading ? (
              <Skeleton className="mx-auto h-40 w-40 rounded-full" />
            ) : (
              <DonutChart slices={slices} totalLabel="Portfolio" className="sm:flex-col" />
            )}
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
