"use client";

import { useEffect, useMemo, useState } from "react";

import { Line } from "react-chartjs-2";

import { Chart as ChartJS, CategoryScale, LinearScale, LineElement, PointElement, Tooltip, Legend } from "chart.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

interface ReturnPoint {
  ts: string;
  value: number;
  return_pct: number | null;
}

interface PortfolioAnalyticsResponse {
  volatility: number;
  max_drawdown: number;
  sharpe_ratio: number | null;
  daily_returns: ReturnPoint[];
}

interface BenchmarkAnalyticsResponse extends PortfolioAnalyticsResponse {
  symbol: string;
  asset_type: string;
}

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.host}`;
  }
  return "http://localhost:8000";
}

export default function AnalyticsPage() {
  const [portfolio, setPortfolio] = useState<PortfolioAnalyticsResponse | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkAnalyticsResponse | null>(null);
  const [benchmarkSymbol, setBenchmarkSymbol] = useState<string>("SPY");

  useEffect(() => {
    async function load() {
      try {
        const apiBase = getApiBase();
        const [pResp, bResp] = await Promise.all([
          fetch(`${apiBase}/api/v1/analytics/portfolio`),
          fetch(`${apiBase}/api/v1/analytics/benchmark?symbol=${encodeURIComponent(benchmarkSymbol)}&asset_type=stock`)
        ]);
        if (pResp.ok) {
          setPortfolio(await pResp.json());
        }
        if (bResp.ok) {
          setBenchmark(await bResp.json());
        }
      } catch {
        // best-effort; errors are surfaced via empty state
      }
    }
    load();
  }, [benchmarkSymbol]);

  const performanceChartData = useMemo(() => {
    if (!portfolio || !portfolio.daily_returns.length) return null;
    const labels = portfolio.daily_returns.map((p) =>
      new Date(p.ts).toLocaleDateString(undefined, { month: "short", day: "numeric" })
    );
    const portfolioValues = portfolio.daily_returns.map((p) => p.value);
    let benchmarkValues: number[] | null = null;
    if (benchmark && benchmark.daily_returns.length) {
      const minLen = Math.min(portfolio.daily_returns.length, benchmark.daily_returns.length);
      benchmarkValues = benchmark.daily_returns.slice(-minLen).map((p) => p.value);
    }

    return {
      labels,
      datasets: [
        {
          label: "Portfolio",
          data: portfolioValues,
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56,189,248,0.2)",
          tension: 0.2
        },
        ...(benchmarkValues
          ? [
              {
                label: benchmark?.symbol ?? "Benchmark",
                data: benchmarkValues,
                borderColor: "#22c55e",
                backgroundColor: "rgba(34,197,94,0.2)",
                tension: 0.2
              }
            ]
          : [])
      ]
    };
  }, [portfolio, benchmark]);

  const drawdownSeries = useMemo(() => {
    if (!portfolio || !portfolio.daily_returns.length) return null;
    const values = portfolio.daily_returns.map((p) => p.value);
    const result: number[] = [];
    let peak = values[0];
    for (const v of values) {
      if (v > peak) peak = v;
      const dd = peak > 0 ? (v - peak) / peak : 0;
      result.push(dd * 100);
    }
    return {
      labels: portfolio.daily_returns.map((p) =>
        new Date(p.ts).toLocaleDateString(undefined, { month: "short", day: "numeric" })
      ),
      datasets: [
        {
          label: "Drawdown (%)",
          data: result,
          borderColor: "#f97316",
          backgroundColor: "rgba(249,115,22,0.2)",
          tension: 0.2
        }
      ]
    };
  }, [portfolio]);

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Analytics</h1>
          <p className="text-sm text-slate-400">
            Portfolio-level risk metrics, performance vs benchmark, and exportable reports.
          </p>
        </div>
        <button
          type="button"
          className="rounded-md bg-brand px-3 py-1.5 text-xs font-medium text-slate-900 hover:bg-brand-light"
          onClick={async () => {
            try {
              const apiBase = getApiBase();
              const resp = await fetch(`${apiBase}/api/v1/reports/portfolio.pdf`, {
                method: "POST"
              });
              if (!resp.ok) return;
              const blob = await resp.blob();
              const url = window.URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = "portfolio-report.pdf";
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
              window.URL.revokeObjectURL(url);
            } catch {
              // ignore errors for now
            }
          }}
        >
          Export PDF
        </button>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-4">
          <p className="text-xs text-slate-400">Volatility</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">
            {portfolio ? (portfolio.volatility * 100).toFixed(2) : "--"}%
          </p>
          <p className="mt-2 text-[11px] text-slate-500">
            Standard deviation of portfolio returns over the sampled window (not annualised).
          </p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-4">
          <p className="text-xs text-slate-400">Max drawdown</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">
            {portfolio ? (portfolio.max_drawdown * 100).toFixed(2) : "--"}%
          </p>
          <p className="mt-2 text-[11px] text-slate-500">
            Largest peak-to-trough decline in portfolio value during the sampled window.
          </p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-4">
          <p className="text-xs text-slate-400">Sharpe ratio (rf=0)</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">
            {portfolio && portfolio.sharpe_ratio != null ? portfolio.sharpe_ratio.toFixed(2) : "--"}
          </p>
          <p className="mt-2 text-[11px] text-slate-500">
            Mean return divided by volatility, using a risk-free rate of 0 for simplicity.
          </p>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="md:col-span-2 rounded-lg border border-slate-800 bg-slate-900/80 p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Portfolio vs benchmark
            </p>
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <span>Benchmark:</span>
              <input
                className="w-20 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs"
                value={benchmarkSymbol}
                onChange={(e) => setBenchmarkSymbol(e.target.value.toUpperCase())}
              />
            </div>
          </div>
          {performanceChartData ? (
            <Line
              data={performanceChartData}
              options={{
                responsive: true,
                plugins: {
                  legend: { display: true },
                  tooltip: { mode: "index", intersect: false }
                },
                scales: {
                  x: { ticks: { maxTicksLimit: 6 } }
                }
              }}
            />
          ) : (
            <p className="text-xs text-slate-500">
              No portfolio data yet. Add holdings to see performance vs benchmark.
            </p>
          )}
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Drawdown
          </p>
          {drawdownSeries ? (
            <Line
              data={drawdownSeries}
              options={{
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                  y: {
                    ticks: {
                      callback: (value) => `${value}%`
                    }
                  }
                }
              }}
            />
          ) : (
            <p className="text-xs text-slate-500">
              Drawdown will appear once there is enough history for your holdings.
            </p>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-slate-800 bg-slate-900/80 p-4">
        <p className="text-[11px] text-slate-500">
          All analytics shown here are derived from historical data and are provided for educational
          purposes only. They do not constitute investment advice or recommendations.
        </p>
      </section>
    </div>
  );
}