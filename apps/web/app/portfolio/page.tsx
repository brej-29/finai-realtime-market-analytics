"use client";

import { useEffect, useMemo, useState } from "react";

import { motion } from "motion/react";
import { Wallet } from "lucide-react";

import { DonutChart } from "@/components/charts/DonutChart";
import { Card, CardContent } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PriceDelta } from "@/components/ui/PriceDelta";
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

  useEffect(() => {
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
    loadHoldings();
  }, []);

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
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {rows.map((r) => (
                    <tr key={r.id} className="hover:bg-surface-hover/60">
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
                    </tr>
                  ))}
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
