"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { motion } from "motion/react";
import { Download, Gauge, LineChart as LineChartIcon, TrendingDown } from "lucide-react";
import { toast } from "sonner";
import { Line } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, Filler, LinearScale, LineElement, PointElement, Tooltip, Legend } from "chart.js";

import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { StatCard } from "@/components/ui/StatCard";
import { apiFetch } from "@/lib/api";
import { cn, formatPercent } from "@/lib/utils";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

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

type BacktestAssetType = "stock" | "crypto";
type BacktestStrategy = "sma_cross" | "rsi_reversion";
type BacktestRangeOption = "6mo" | "1y";

interface EquityPoint {
  date: string;
  strategy: number;
  buy_hold: number;
}

interface BacktestResult {
  symbol: string;
  asset_type: BacktestAssetType;
  strategy: BacktestStrategy;
  range: string;
  bars_used: number;
  total_return_pct: number;
  buy_hold_return_pct: number;
  cagr_pct: number;
  sharpe: number;
  max_drawdown_pct: number;
  win_rate_pct: number | null;
  num_trades: number;
  equity_curve: EquityPoint[];
}

function toneForReturn(value: number): "positive" | "negative" | "neutral" {
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}

const metricToneClasses: Record<"neutral" | "positive" | "negative", string> = {
  neutral: "text-foreground",
  positive: "text-positive",
  negative: "text-negative"
};

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      labels: { color: "rgb(148 158 171)", boxWidth: 10, boxHeight: 10 }
    },
    tooltip: { mode: "index" as const, intersect: false }
  },
  scales: {
    x: {
      ticks: { maxTicksLimit: 6, color: "rgb(148 158 171)" },
      grid: { color: "rgba(255,255,255,0.04)" }
    },
    y: {
      ticks: { color: "rgb(148 158 171)" },
      grid: { color: "rgba(255,255,255,0.04)" }
    }
  }
};

export default function AnalyticsPage() {
  const [portfolio, setPortfolio] = useState<PortfolioAnalyticsResponse | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkAnalyticsResponse | null>(null);
  const [benchmarkSymbol, setBenchmarkSymbol] = useState<string>("SPY");
  const [exporting, setExporting] = useState(false);

  const [btSymbol, setBtSymbol] = useState("");
  const [btAssetType, setBtAssetType] = useState<BacktestAssetType>("stock");
  const [btStrategy, setBtStrategy] = useState<BacktestStrategy>("sma_cross");
  const [btRange, setBtRange] = useState<BacktestRangeOption>("1y");
  const [btResult, setBtResult] = useState<BacktestResult | null>(null);
  const [btRunning, setBtRunning] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [pResp, bResp] = await Promise.all([
          apiFetch("/api/v1/analytics/portfolio"),
          apiFetch(`/api/v1/analytics/benchmark?symbol=${encodeURIComponent(benchmarkSymbol)}&asset_type=stock`)
        ]);
        if (pResp.ok) setPortfolio(await pResp.json());
        if (bResp.ok) setBenchmark(await bResp.json());
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
          borderColor: "#14B8A6",
          backgroundColor: "rgba(20,184,166,0.15)",
          tension: 0.3,
          fill: true
        },
        ...(benchmarkValues
          ? [
              {
                label: benchmark?.symbol ?? "Benchmark",
                data: benchmarkValues,
                borderColor: "#818CF8",
                backgroundColor: "rgba(129,140,248,0.1)",
                tension: 0.3,
                fill: true
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
          borderColor: "#F97316",
          backgroundColor: "rgba(249,115,22,0.15)",
          tension: 0.3,
          fill: true
        }
      ]
    };
  }, [portfolio]);

  async function handleExport() {
    setExporting(true);
    try {
      const resp = await apiFetch("/api/v1/reports/portfolio.pdf", { method: "POST" });
      if (!resp.ok) throw new Error("export failed");
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "portfolio-report.pdf";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success("Report downloaded");
    } catch {
      toast.error("Could not generate report. Please try again.");
    } finally {
      setExporting(false);
    }
  }

  const backtestChartData = useMemo(() => {
    if (!btResult || !btResult.equity_curve.length) return null;
    const labels = btResult.equity_curve.map((p) =>
      new Date(p.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })
    );
    return {
      labels,
      datasets: [
        {
          label: "Strategy",
          data: btResult.equity_curve.map((p) => p.strategy),
          borderColor: "#14B8A6",
          backgroundColor: "rgba(20,184,166,0.15)",
          tension: 0.3,
          fill: true
        },
        {
          label: "Buy & Hold",
          data: btResult.equity_curve.map((p) => p.buy_hold),
          borderColor: "#94A3B8",
          backgroundColor: "rgba(148,163,184,0.08)",
          tension: 0.3,
          fill: false
        }
      ]
    };
  }, [btResult]);

  async function handleBacktest(e: FormEvent) {
    e.preventDefault();
    const trimmed = btSymbol.trim().toUpperCase();
    if (!trimmed || btRunning) return;
    setBtRunning(true);
    try {
      const resp = await apiFetch("/api/v1/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: trimmed,
          asset_type: btAssetType,
          strategy: btStrategy,
          range: btRange
        })
      });
      const data = await resp.json().catch(() => null);
      if (!resp.ok) {
        toast.error(data?.message ?? "Backtest failed. Please check the inputs and try again.");
        return;
      }
      setBtResult(data);
    } catch {
      toast.error("Could not reach the API. Please try again.");
    } finally {
      setBtRunning(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-7xl space-y-6"
    >
      <header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">Analytics</h1>
          <p className="text-sm text-muted">
            Portfolio-level risk metrics, performance vs benchmark, and exportable reports.
          </p>
        </div>
        <Button onClick={handleExport} disabled={exporting} size="sm">
          <Download className="h-3.5 w-3.5" />
          {exporting ? "Generating…" : "Export PDF"}
        </Button>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Volatility"
          value={(portfolio?.volatility ?? 0) * 100}
          formatter={(v) => `${v.toFixed(2)}%`}
          icon={<LineChartIcon className="h-4 w-4" />}
          helper="Std. deviation of returns over the sampled window (not annualised)."
        />
        <StatCard
          label="Max Drawdown"
          value={(portfolio?.max_drawdown ?? 0) * 100}
          formatter={(v) => `${v.toFixed(2)}%`}
          icon={<TrendingDown className="h-4 w-4" />}
          tone={portfolio && portfolio.max_drawdown < 0 ? "negative" : "neutral"}
          helper="Largest peak-to-trough decline in portfolio value."
        />
        <StatCard
          label="Sharpe Ratio (rf=0)"
          value={portfolio?.sharpe_ratio ?? 0}
          formatter={(v) => (portfolio?.sharpe_ratio != null ? v.toFixed(2) : "—")}
          icon={<Gauge className="h-4 w-4" />}
          helper="Mean return divided by volatility, risk-free rate of 0."
        />
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardContent className="pt-5">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                Portfolio vs benchmark
              </p>
              <div className="flex items-center gap-2 text-xs text-muted">
                <span>Benchmark:</span>
                <Input
                  value={benchmarkSymbol}
                  onChange={(e) => setBenchmarkSymbol(e.target.value.toUpperCase())}
                  className="h-8 w-20 text-xs"
                />
              </div>
            </div>
            <div className="h-64">
              {performanceChartData ? (
                <Line data={performanceChartData} options={chartOptions} />
              ) : (
                <p className="text-xs text-muted">
                  No portfolio data yet. Add holdings to see performance vs benchmark.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">Drawdown</p>
            <div className="h-64">
              {drawdownSeries ? (
                <Line
                  data={drawdownSeries}
                  options={{
                    ...chartOptions,
                    plugins: { ...chartOptions.plugins, legend: { display: false } },
                    scales: {
                      ...chartOptions.scales,
                      y: { ...chartOptions.scales.y, ticks: { callback: (v) => `${v}%`, color: "rgb(148 158 171)" } }
                    }
                  }}
                />
              ) : (
                <p className="text-xs text-muted">
                  Drawdown will appear once there is enough history for your holdings.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardContent className="py-3.5">
          <p className="text-[11px] text-muted">
            All analytics shown here are derived from historical data and are provided for educational
            purposes only. They do not constitute investment advice or recommendations.
          </p>
        </CardContent>
      </Card>

      <section className="space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Strategy Backtest</h2>
          <p className="text-xs text-muted">
            Simulate a rules-based strategy against buy-and-hold on historical price data.
          </p>
        </div>

        <Card className="p-4">
          <form onSubmit={handleBacktest} className="flex flex-wrap gap-2.5">
            <Input
              type="text"
              placeholder={btAssetType === "crypto" ? "Symbol (e.g. BTC)" : "Symbol (e.g. AAPL)"}
              value={btSymbol}
              onChange={(e) => setBtSymbol(e.target.value)}
              className="min-w-[160px] flex-1"
            />
            <Select
              value={btAssetType}
              onChange={(e) => setBtAssetType(e.target.value as BacktestAssetType)}
              aria-label="Asset type"
            >
              <option value="stock">Stock</option>
              <option value="crypto">Crypto</option>
            </Select>
            <Select
              value={btStrategy}
              onChange={(e) => setBtStrategy(e.target.value as BacktestStrategy)}
              aria-label="Strategy"
            >
              <option value="sma_cross">SMA crossover</option>
              <option value="rsi_reversion">RSI mean-reversion</option>
            </Select>
            <Select
              value={btRange}
              onChange={(e) => setBtRange(e.target.value as BacktestRangeOption)}
              aria-label="Backtest range"
            >
              <option value="6mo">6 months</option>
              <option value="1y">1 year</option>
            </Select>
            <Button type="submit" disabled={btRunning || !btSymbol.trim()}>
              {btRunning ? "Backtesting…" : "Run backtest"}
            </Button>
          </form>
        </Card>

        {!btResult && !btRunning && (
          <p className="text-xs text-muted">
            Configure a symbol and strategy above, then run a backtest to see performance metrics and an
            equity curve.
          </p>
        )}

        {btResult && (
          <>
            <Card>
              <CardContent className="grid grid-cols-2 gap-3 pt-5 sm:grid-cols-4">
                <div className="rounded-xl border bg-surface/40 p-3">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Total Return</p>
                  <p
                    className={cn(
                      "mt-1 text-lg font-semibold tabular-nums",
                      metricToneClasses[toneForReturn(btResult.total_return_pct)]
                    )}
                  >
                    {formatPercent(btResult.total_return_pct)}
                  </p>
                </div>
                <div className="rounded-xl border bg-surface/40 p-3">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Buy &amp; Hold</p>
                  <p
                    className={cn(
                      "mt-1 text-lg font-semibold tabular-nums",
                      metricToneClasses[toneForReturn(btResult.buy_hold_return_pct)]
                    )}
                  >
                    {formatPercent(btResult.buy_hold_return_pct)}
                  </p>
                </div>
                <div className="rounded-xl border bg-surface/40 p-3">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted">CAGR</p>
                  <p
                    className={cn(
                      "mt-1 text-lg font-semibold tabular-nums",
                      metricToneClasses[toneForReturn(btResult.cagr_pct)]
                    )}
                  >
                    {formatPercent(btResult.cagr_pct)}
                  </p>
                </div>
                <div className="rounded-xl border bg-surface/40 p-3">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Sharpe</p>
                  <p className="mt-1 text-lg font-semibold tabular-nums text-foreground">
                    {btResult.sharpe.toFixed(2)}
                  </p>
                </div>
                <div className="rounded-xl border bg-surface/40 p-3">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Max Drawdown</p>
                  <p
                    className={cn(
                      "mt-1 text-lg font-semibold tabular-nums",
                      metricToneClasses[btResult.max_drawdown_pct < 0 ? "negative" : "neutral"]
                    )}
                  >
                    {formatPercent(btResult.max_drawdown_pct)}
                  </p>
                </div>
                <div className="rounded-xl border bg-surface/40 p-3">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Win Rate</p>
                  <p className="mt-1 text-lg font-semibold tabular-nums text-foreground">
                    {btResult.win_rate_pct != null ? `${btResult.win_rate_pct.toFixed(2)}%` : "—"}
                  </p>
                </div>
                <div className="rounded-xl border bg-surface/40 p-3">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Trades</p>
                  <p className="mt-1 text-lg font-semibold tabular-nums text-foreground">
                    {btResult.num_trades}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-5">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
                  Strategy vs Buy &amp; Hold (normalized to 100)
                </p>
                <div className="h-72">
                  {backtestChartData && <Line data={backtestChartData} options={chartOptions} />}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-3.5">
                <p className="text-[11px] text-muted">
                  Backtest results are simulated from historical data and do not model transaction costs,
                  slippage, taxes, or execution delays. Past performance is not indicative of future results
                  and does not constitute investment advice.
                </p>
              </CardContent>
            </Card>
          </>
        )}
      </section>
    </motion.div>
  );
}
