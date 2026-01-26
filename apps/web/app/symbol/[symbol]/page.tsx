"use client";

import { useEffect, useMemo, useState } from "react";

import {
  CandlestickChart,
  type CandlePoint,
  type IndicatorSeries
} from "../../../components/charts/CandlestickChart";
import { useRealtimePrices } from "../../../hooks/useRealtimePrices";

interface HistoryBar {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
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

export default function SymbolDetailPage({ params }: PageProps) {
  const [history, setHistory] = useState<HistoryBar[]>([]);
  const symbol = params.symbol.toUpperCase();
  const { status, ticks } = useRealtimePrices({ symbols: [symbol], assetType: "stock" });
  const latest = ticks[symbol];

  useEffect(() => {
    async function loadHistory() {
      try {
        const apiBase =
          process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
        const url = new URL(`${apiBase}/api/v1/history`);
        url.searchParams.set("symbol", symbol);
        url.searchParams.set("asset_type", "stock");
        url.searchParams.set("interval", "1h");
        url.searchParams.set("range", "1d");
        const resp = await fetch(url.toString());
        if (!resp.ok) return;
        const data = await resp.json();
        setHistory(data.bars ?? []);
      } catch {
        // ignore
      }
    }
    loadHistory();
  }, [symbol]);

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

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{symbol}</h1>
          <p className="text-sm text-slate-400">
            Intraday performance with technical indicators (MA, Bollinger).
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
            The moving average smooths out price action to highlight trends by averaging
            the last 20 closes.
          </p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm">
          <h2 className="text-slate-200">Bollinger Bands</h2>
          <p className="mt-1 text-slate-400">
            Upper and lower bands are based on standard deviations around the moving
            average and can highlight volatility.
          </p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm">
          <h2 className="text-slate-200">RSI &amp; MACD (future work)</h2>
          <p className="mt-1 text-slate-400">
            RSI and MACD panels will be implemented in the next prompt to complete the
            indicator suite.
          </p>
        </div>
      </div>
    </div>
  );
}