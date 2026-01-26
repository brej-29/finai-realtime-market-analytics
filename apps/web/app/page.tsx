"use client";

import { useEffect } from "react";

import { WebSocketStatus } from "../components/realtime/WebSocketStatus";
import { useRealtimePrices } from "../hooks/useRealtimePrices";
import { useAppStore } from "../store/useAppStore";

export default function HomePage() {
  const { status, ticks } = useRealtimePrices({ symbols: ["AAPL", "BTC"], assetType: "stock" });
  const { serverStatus, setServerStatus } = useAppStore();

  useEffect(() => {
    async function checkHealth() {
      try {
        const apiBase =
          process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
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

    checkHealth();
  }, [setServerStatus]);

  const latestAapl = ticks["AAPL"];

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
          <p className="mt-3 text-2xl font-semibold">$0.00</p>
          <p className="mt-1 text-xs text-slate-500">
            Connect your holdings in the Portfolio tab.
          </p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-400">P&amp;L Today</p>
          <p className="mt-3 text-2xl font-semibold text-emerald-400">+0.00%</p>
          <p className="mt-1 text-xs text-slate-500">
            Live P&amp;L will update as you add holdings.
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

      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="text-sm font-semibold text-slate-200">Next steps</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-400">
          <li>Add symbols to your Watchlist for real-time tracking.</li>
          <li>Configure holdings in the Portfolio page to see P&amp;L.</li>
          <li>Create price alerts to be notified about key levels.</li>
        </ul>
      </div>
    </div>
  );
}