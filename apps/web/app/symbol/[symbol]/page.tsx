"use client";

import { Suspense, useEffect, useMemo, useState } from "react";

import { useSearchParams } from "next/navigation";

import {
  CandlestickChart,
  type CandlePoint,
  type IndicatorSeries
} from "../../../components/charts/CandlestickChart";
import { useRealtimePrices, type AssetType } from "../../../hooks/useRealtimePrices";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  Legend
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

interface HistoryBar {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface NewsItem {
  title: string;
  url: string;
  published_at: string;
  source?: string | null;
  sentiment: {
    score: number;
    label: "positive" | "neutral" | "negative";
    explanation: string;
  };
}

interface AIInsights {
  technical_summary: {
    rsi: number | null;
    rsi_label: string | null;
    macd: number | null;
    macd_signal: number | null;
    macd_histogram: number | null;
    macd_label: string | null;
  };
  forecast_summary: {
    direction: "up" | "down" | "flat";
    confidence: number | null;
    horizon_days: number | null;
    points: {
      ts: string;
      value: number;
      lower: number;
      upper: number;
    }[];
  } | null;
  anomalies: {
    ts: string;
    value: number;
    score: number;
    is_anomaly: boolean;
  }[];
  disclaimer: string;
}

interface PageProps {
  params: { symbol: string };
}

function computeIndicators(candles: CandlePoint[]): IndicatorSeries {
  const maPeriod = 20;
  const ma: IndicatorSeries["ma"] = [];
  const upperBand: IndicatorSeries["upperBand"] = [];
  const lowerBand: IndicatorSeries["lowerBand"] = [];

  for (let i = 0; i < candles.length; i += 1) {
    if (i + 1 < maPeriod) continue;
    const window = candles.slice(i + 1 - maPeriod, i + 1);
    const closes = window.map((c) => c.close);
    const mean = closes.reduce((a, b) => a + b, 0) / closes.length;
    const variance =
      closes.reduce((sum, c) => sum + (c - mean) * (c - mean), 0) / closes.length;
    const stddev = Math.sqrt(variance);
    const time = candles[i].time as any;
    ma?.push({ time, value: mean });
    upperBand?.push({ time, value: mean + 2 * stddev });
    lowerBand?.push({ time, value: mean - 2 * stddev });
  }

  return {
    ma: ma ?? undefined,
    upperBand: upperBand ?? undefined,
    lowerBand: lowerBand ?? undefined
  };
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

function SymbolDetail({ params }: PageProps) {
  const [history, setHistory] = useState<HistoryBar[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [newsUpdatedAt, setNewsUpdatedAt] = useState<string | null>(null);
  const [aiInsights, setAiInsights] = useState<AIInsights | null>(null);

  const symbol = params.symbol.toUpperCase();
  const searchParams = useSearchParams();
  const assetType: AssetType =
    searchParams.get("asset_type") === "crypto" ? "crypto" : "stock";
  const { status, ticks } = useRealtimePrices({ symbols: [symbol], assetType });
  const latest = ticks[symbol];

  useEffect(() => {
    async function loadHistoryAndInsights() {
      try {
        const apiBase = getApiBase();
        const historyUrl = new URL(`${apiBase}/api/v1/history`);
        historyUrl.searchParams.set("symbol", symbol);
        historyUrl.searchParams.set("asset_type", assetType);
        historyUrl.searchParams.set("interval", "1h");
        historyUrl.searchParams.set("range", "1d");

        const [historyResp, newsResp, aiResp] = await Promise.all([
          fetch(historyUrl.toString()),
          fetch(`${apiBase}/api/v1/news?symbol=${symbol}&asset_type=${assetType}`),
          fetch(`${apiBase}/api/v1/ai/insights?symbol=${symbol}&asset_type=${assetType}`)
        ]);

        if (historyResp.ok) {
          const data = await historyResp.json();
          setHistory(data.bars ?? []);
        }

        if (newsResp.ok) {
          const data = await newsResp.json();
          setNews(data.items ?? []);
          setNewsUpdatedAt(data.last_updated ?? null);
        }

        if (aiResp.ok) {
          const data = await aiResp.json();
          setAiInsights(data);
        }
      } catch {
        // ignore network errors; panels will show empty states
      }
    }
    loadHistoryAndInsights();
  }, [symbol, assetType]);

  const candles: CandlePoint[] = useMemo(
    () =>
      history.map((b) => ({
        time: Math.floor(new Date(b.ts).getTime() / 1000),
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close
      })),
    [history]
  );

  const indicators = useMemo<IndicatorSeries>(() => computeIndicators(candles), [candles]);

  const forecastChartData = useMemo(() => {
    if (!aiInsights || !aiInsights.forecast_summary) return null;
    const pts = aiInsights.forecast_summary.points;
    return {
      labels: pts.map((p) =>
        new Date(p.ts).toLocaleDateString(undefined, { month: "short", day: "numeric" })
      ),
      datasets: [
        {
          label: "Forecast",
          data: pts.map((p) => p.value),
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56,189,248,0.2)",
          tension: 0.2
        }
      ]
    };
  }, [aiInsights]);

  const sentimentScore = useMemo(() => {
    if (!news.length) return null;
    const scores = news.map((n) => n.sentiment.score);
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    return avg;
  }, [news]);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold">{symbol}</h1>
            <span className="rounded-full border border-slate-700 bg-slate-800/80 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-300">
              {assetType}
            </span>
          </div>
          <p className="text-sm text-slate-400">
            Intraday performance with technical indicators, news, and lightweight AI insights.
          </p>
        </div>
        <div className="text-right text-sm">
          <p className="text-slate-400">Realtime price</p>
          {latest ? (
            <p className="text-xl font-semibold text-slate-100">${latest.price.toFixed(2)}</p>
          ) : (
            <p className="text-sm text-slate-500">Waiting for data…</p>
          )}
          <p className="mt-1 text-xs text-slate-500 capitalize">{status}</p>
        </div>
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <CandlestickChart candles={candles} indicators={indicators} />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm">
          <h2 className="text-slate-200">Moving Average (MA20)</h2>
          <p className="mt-1 text-slate-400">
            The moving average smooths out price action to highlight trends by averaging the last 20
            closes.
          </p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm">
          <h2 className="text-slate-200">Bollinger Bands</h2>
          <p className="mt-1 text-slate-400">
            Upper and lower bands are based on standard deviations around the moving average and can
            highlight volatility.
          </p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm">
          <h2 className="text-slate-200">RSI &amp; MACD</h2>
          <p className="mt-1 text-slate-400">
            {aiInsights?.technical_summary.rsi_label ?? "RSI and MACD will appear once data loads."}
          </p>
          {aiInsights?.technical_summary.macd_label && (
            <p className="mt-1 text-slate-400">{aiInsights.technical_summary.macd_label}</p>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm md:col-span-2">
          <h2 className="text-slate-200">News &amp; Sentiment</h2>
          {sentimentScore != null && (
            <p className="mt-1 text-xs text-slate-400">
              Average sentiment score (VADER, -1 to 1):{" "}
              <span className="font-semibold text-slate-100">{sentimentScore.toFixed(2)}</span>
            </p>
          )}
          {newsUpdatedAt && (
            <p className="mt-1 text-[11px] text-slate-500">
              Last updated from GDELT:{" "}
              {new Date(newsUpdatedAt).toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit"
              })}
            </p>
          )}
          <div className="mt-3 space-y-2">
            {news.length === 0 && (
              <p className="text-xs text-slate-500">
                No recent headlines found for this symbol in the GDELT feed.
              </p>
            )}
            {news.map((item) => (
              <div key={item.url} className="border-b border-slate-800 pb-2 last:border-b-0">
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-medium text-slate-100 hover:text-brand-light"
                >
                  {item.title}
                </a>
                <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                  <span>{item.source ?? "Unknown source"}</span>
                  <span>
                    {new Date(item.published_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric"
                    })}
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-slate-500">
                  Sentiment: {item.sentiment.label} ({item.sentiment.score.toFixed(2)}).{" "}
                  {item.sentiment.explanation}
                </p>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm">
          <h2 className="text-slate-200">AI Forecast</h2>
          {aiInsights?.forecast_summary && forecastChartData ? (
            <>
              <p className="mt-1 text-xs text-slate-400">
                Model direction:{" "}
                <span className="font-semibold text-slate-100">
                  {aiInsights.forecast_summary.direction}
                </span>{" "}
                {aiInsights.forecast_summary.confidence != null && (
                  <span>
                    (confidence ~{" "}
                    {(aiInsights.forecast_summary.confidence * 100).toFixed(0)}
                    %)
                  </span>
                )}
              </p>
              <div className="mt-3 h-40">
                <Line
                  data={forecastChartData}
                  options={{
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                      x: { ticks: { maxTicksLimit: 4 } }
                    }
                  }}
                />
              </div>
            </>
          ) : (
            <p className="mt-1 text-xs text-slate-500">
              Forecast appears once there is enough history for this symbol.
            </p>
          )}
          {aiInsights && (
            <p className="mt-3 text-[10px] text-slate-500">{aiInsights.disclaimer}</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function SymbolDetailPage(props: PageProps) {
  // useSearchParams requires a Suspense boundary in the App Router.
  return (
    <Suspense fallback={null}>
      <SymbolDetail {...props} />
    </Suspense>
  );
}