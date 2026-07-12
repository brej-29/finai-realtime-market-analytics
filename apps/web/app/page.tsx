"use client";

import { useEffect, useState } from "react";

import Link from "next/link";

import { WebSocketStatus } from "../components/realtime/WebSocketStatus";
import { useRealtimePrices } from "../hooks/useRealtimePrices";
import { useAppStore } from "../store/useAppStore";

interface PortfolioSummaryByType {
  asset_type: "stock" | "crypto";
  cost_basis: number;
  market_value: number;
  unrealized_pnl: number;
  weight: number | null;
}

interface PortfolioSummary {
  total_cost_basis: number;
  total_market_value: number;
  total_unrealized_pnl: number;
  by_asset_type: Record<string, PortfolioSummaryByType>;
}

function formatCurrency(value: number): string {
  return value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  });
}

export default function HomePage() {
  const { status, ticks } = useRealtimePrices({ symbols: ["AAPL", "MSFT"], assetType: "stock" });
  const { serverStatus, setServerStatus } = useAppStore();
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;

    async function checkHealth() {
      try {
        const resp = await fetch(`${apiBase}/health`);
        setServerStatus({
          apiHealthy: resp.ok,
          lastChecked: new Date().toISOString()
        });
      } catch {
        setServerStatus({
          apiHealthy: false,
          lastChecked: new Date().toISOString()
        });
      }
    }

    async function loadSummary() {
      try {
        const resp = await fetch(`${apiBase}/api/v1/portfolio/summary`);
        if (resp.ok) {
          setSummary(await resp.json());
        }
      } catch {
        // API unreachable; the empty state below covers this.
      } finally {
        setSummaryLoading(false);
      }
    }

    checkHealth();
    loadSummary();
  }, [setServerStatus]);

  const latestAapl = ticks["AAPL"];
  const hasHoldings = (summary?.total_cost_basis ?? 0) > 0;
  const pnl = summary?.total_unrealized_pnl ?? 0;
  const pnlPct = hasHoldings && summary ? (pnl / summary.total_cost_basis) * 100 : 0;
  const pnlPositive = pnl >= 0;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Portfolio Overview</h1>
          <p className="text-sm text-slate-400">
            Real-time insights for your stock &amp; crypto holdings.
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex flex-col items-end">
            <span className="text-slate-400">Server Status</span>
            <span
              className={`text-xs ${
                serverStatus.apiHealthy ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {serverStatus.apiHealthy ? "API healthy" : "API unreachable"}
            </span>
          </div>
          <WebSocketStatus status={status} />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-400">
            Total Market Value
          </p>
          <p className="mt-3 text-2xl font-semibold">
            {summaryLoading ? "…" : formatCurrency(summary?.total_market_value ?? 0)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {hasHoldings && summary ? (
              <>Cost basis: {formatCurrency(summary.total_cost_basis)}</>
            ) : (
              <>
                Add holdings in the{" "}
                <Link href="/portfolio" className="text-brand-light hover:underline">
                  Portfolio
                </Link>{" "}
                tab to see live valuations.
              </>
            )}
          </p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-400">Unrealized P&amp;L</p>
          <p
            className={`mt-3 text-2xl font-semibold ${
              pnlPositive ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {summaryLoading
              ? "…"
              : `${pnlPositive ? "+" : ""}${formatCurrency(pnl)}`}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {hasHoldings
              ? `${pnlPositive ? "+" : ""}${pnlPct.toFixed(2)}% vs. cost basis`
              : "Live P&L will update as you add holdings."}
          </p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-400">
            Sample Live Tick
          </p>
          {latestAapl ? (
            <div className="mt-3">
              <p className="text-sm text-slate-300">
                AAPL <span className="text-xs text-slate-500">(demo)</span>
              </p>
              <p className="text-xl font-semibold">${latestAapl.price.toFixed(2)}</p>
              {typeof latestAapl.change24h === "number" && (
                <p
                  className={`text-xs ${
                    latestAapl.change24h >= 0 ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  24h: {latestAapl.change24h.toFixed(2)}%
                </p>
              )}
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-500">
              Waiting for live ticks over WebSocket or REST fallback…
            </p>
          )}
        </div>
      </div>

      {hasHoldings && summary && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="text-sm font-semibold text-slate-200">Allocation by asset class</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {Object.values(summary.by_asset_type).map((entry) => {
              const entryPositive = entry.unrealized_pnl >= 0;
              return (
                <div
                  key={entry.asset_type}
                  className="rounded-md border border-slate-800 bg-slate-950/40 p-3 text-sm"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium capitalize text-slate-200">
                      {entry.asset_type}
                    </span>
                    <span className="text-xs text-slate-400">
                      {((entry.weight ?? 0) * 100).toFixed(1)}% of portfolio
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-xs">
                    <span className="text-slate-400">
                      {formatCurrency(entry.market_value)}
                    </span>
                    <span className={entryPositive ? "text-emerald-400" : "text-red-400"}>
                      {entryPositive ? "+" : ""}
                      {formatCurrency(entry.unrealized_pnl)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="text-sm font-semibold text-slate-200">Next steps</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-400">
          <li>
            Add symbols to your{" "}
            <Link href="/watchlist" className="text-brand-light hover:underline">
              Watchlist
            </Link>{" "}
            for real-time tracking.
          </li>
          <li>
            Configure holdings in the{" "}
            <Link href="/portfolio" className="text-brand-light hover:underline">
              Portfolio
            </Link>{" "}
            page to see P&amp;L.
          </li>
          <li>
            Create price{" "}
            <Link href="/alerts" className="text-brand-light hover:underline">
              alerts
            </Link>{" "}
            to be notified about key levels.
          </li>
        </ul>
      </div>
    </div>
  );
}
