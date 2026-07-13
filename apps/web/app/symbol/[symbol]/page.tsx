"use client";

import { Suspense, useEffect, useMemo, useState } from "react";

import { useSearchParams } from "next/navigation";
import { motion } from "motion/react";
import { Activity, Gauge, Newspaper, Sparkles, TrendingUp } from "lucide-react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  Filler,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip as ChartTooltip,
  Legend
} from "chart.js";

import {
  CandlestickChart,
  type CandlePoint,
  type IndicatorSeries
} from "@/components/charts/CandlestickChart";
import { useRealtimePrices, type AssetType } from "@/hooks/useRealtimePrices";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent } from "@/components/ui/Card";
import { PriceDelta } from "@/components/ui/PriceDelta";
import { Skeleton } from "@/components/ui/Skeleton";
import { WebSocketStatus } from "@/components/realtime/WebSocketStatus";
import { cn, formatCurrency, relativeTime } from "@/lib/utils";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, ChartTooltip, Legend);

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
    points: { ts: string; value: number; lower: number; upper: number }[];
  } | null;
  anomalies: { ts: string; value: number; score: number; is_anomaly: boolean }[];
  disclaimer: string;
}

interface PageProps {
  params: { symbol: string };
}

const sentimentTone: Record<NewsItem["sentiment"]["label"], "positive" | "negative" | "default"> = {
  positive: "positive",
  negative: "negative",
  neutral: "default"
};

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

  return { ma: ma ?? undefined, upperBand: upperBand ?? undefined, lowerBand: lowerBand ?? undefined };
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
  const [loading, setLoading] = useState(true);

  const symbol = params.symbol.toUpperCase();
  const searchParams = useSearchParams();
  const assetType: AssetType = searchParams.get("asset_type") === "crypto" ? "crypto" : "stock";
  const { status, ticks } = useRealtimePrices({ symbols: [symbol], assetType });
  const latest = ticks[symbol];

  useEffect(() => {
    async function loadHistoryAndInsights() {
      setLoading(true);
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
          setAiInsights(await aiResp.json());
        }
      } catch {
        // ignore network errors; panels will show empty states
      } finally {
        setLoading(false);
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
      labels: pts.map((p) => new Date(p.ts).toLocaleDateString(undefined, { month: "short", day: "numeric" })),
      datasets: [
        {
          label: "Forecast",
          data: pts.map((p) => p.value),
          borderColor: "#14B8A6",
          backgroundColor: "rgba(20,184,166,0.15)",
          tension: 0.3,
          fill: true
        }
      ]
    };
  }, [aiInsights]);

  const sentimentScore = useMemo(() => {
    if (!news.length) return null;
    const scores = news.map((n) => n.sentiment.score);
    return scores.reduce((a, b) => a + b, 0) / scores.length;
  }, [news]);

  const priceChangePct = latest?.change24h ?? null;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-wrap items-center justify-between gap-4"
      >
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">{symbol}</h1>
            <Badge variant="outline" className="uppercase">
              {assetType}
            </Badge>
          </div>
          <p className="text-sm text-muted">
            Intraday performance with technical indicators, news, and AI insights.
          </p>
        </div>
        <div className="text-right">
          {latest ? (
            <>
              <p className="text-2xl font-semibold tabular-nums text-foreground">
                {formatCurrency(latest.price)}
              </p>
              <div className="mt-1 flex items-center justify-end gap-2">
                <PriceDelta value={priceChangePct} />
                <WebSocketStatus status={status} />
              </div>
            </>
          ) : (
            <div className="flex flex-col items-end gap-2">
              <Skeleton className="h-7 w-24" />
              <WebSocketStatus status={status} />
            </div>
          )}
        </div>
      </motion.div>

      <Card className="p-4">
        {loading && candles.length === 0 ? (
          <Skeleton className="h-80 w-full" />
        ) : (
          <CandlestickChart candles={candles} indicators={indicators} />
        )}
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="p-4 text-sm">
          <div className="flex items-center gap-2 text-foreground">
            <TrendingUp className="h-4 w-4 text-brand-light" />
            <h2 className="font-medium">Moving Average (MA20)</h2>
          </div>
          <p className="mt-2 text-xs text-muted">
            Smooths price action to highlight trend direction over the last 20 closes.
          </p>
        </Card>
        <Card className="p-4 text-sm">
          <div className="flex items-center gap-2 text-foreground">
            <Activity className="h-4 w-4 text-brand-light" />
            <h2 className="font-medium">Bollinger Bands</h2>
          </div>
          <p className="mt-2 text-xs text-muted">
            Upper/lower bands from standard deviation around the moving average — width signals volatility.
          </p>
        </Card>
        <Card className="p-4 text-sm">
          <div className="flex items-center gap-2 text-foreground">
            <Gauge className="h-4 w-4 text-brand-light" />
            <h2 className="font-medium">RSI &amp; MACD</h2>
          </div>
          <p className="mt-2 text-xs text-muted">
            {aiInsights?.technical_summary.rsi_label ?? "Will appear once data loads."}
          </p>
          {aiInsights?.technical_summary.macd_label && (
            <p className="mt-1 text-xs text-muted">{aiInsights.technical_summary.macd_label}</p>
          )}
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardContent className="pt-5">
            <div className="mb-1 flex items-center gap-2">
              <Newspaper className="h-4 w-4 text-brand-light" />
              <h2 className="text-sm font-medium text-foreground">News &amp; Sentiment</h2>
            </div>
            {sentimentScore != null && (
              <p className="text-xs text-muted">
                Average sentiment (VADER, -1 to 1):{" "}
                <span className="font-semibold tabular-nums text-foreground">
                  {sentimentScore.toFixed(2)}
                </span>
              </p>
            )}
            {newsUpdatedAt && (
              <p className="mt-1 text-[11px] text-muted">
                Last updated {relativeTime(newsUpdatedAt)}
              </p>
            )}
            <div className="mt-3 space-y-2.5">
              {news.length === 0 && (
                <p className="text-xs text-muted">
                  No recent headlines found for this symbol in the GDELT feed.
                </p>
              )}
              {news.map((item) => (
                <div key={item.url} className="border-b border-border pb-2.5 last:border-b-0 last:pb-0">
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-medium text-foreground hover:text-brand-light"
                  >
                    {item.title}
                  </a>
                  <div className="mt-1 flex items-center justify-between text-[11px] text-muted">
                    <span>{item.source ?? "Unknown source"}</span>
                    <span>{relativeTime(item.published_at)}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-1.5">
                    <Badge variant={sentimentTone[item.sentiment.label]}>{item.sentiment.label}</Badge>
                    <span className="text-[11px] text-muted">{item.sentiment.explanation}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-5">
            <div className="mb-1 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-brand-light" />
              <h2 className="text-sm font-medium text-foreground">AI Forecast</h2>
            </div>
            {aiInsights?.forecast_summary && forecastChartData ? (
              <>
                <p className="text-xs text-muted">
                  Direction:{" "}
                  <span
                    className={cn(
                      "font-semibold capitalize",
                      aiInsights.forecast_summary.direction === "up" && "text-positive",
                      aiInsights.forecast_summary.direction === "down" && "text-negative"
                    )}
                  >
                    {aiInsights.forecast_summary.direction}
                  </span>
                  {aiInsights.forecast_summary.confidence != null && (
                    <span> (~{(aiInsights.forecast_summary.confidence * 100).toFixed(0)}% conf.)</span>
                  )}
                </p>
                <div className="mt-3 h-40">
                  <Line
                    data={forecastChartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: { legend: { display: false } },
                      scales: { x: { ticks: { maxTicksLimit: 4 } } }
                    }}
                  />
                </div>
              </>
            ) : (
              <p className="text-xs text-muted">
                Forecast appears once there is enough history for this symbol.
              </p>
            )}
            {aiInsights && <p className="mt-3 text-[10px] text-muted">{aiInsights.disclaimer}</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function SymbolDetailPage(props: PageProps) {
  return (
    <Suspense fallback={null}>
      <SymbolDetail {...props} />
    </Suspense>
  );
}
