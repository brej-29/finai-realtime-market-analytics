"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ISeriesApi,
  IChartApi,
  CandlestickData,
  LineData
} from "lightweight-charts";

export interface CandlePoint {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface IndicatorSeries {
  ma?: LineData[];
  upperBand?: LineData[];
  lowerBand?: LineData[];
}

interface Props {
  candles: CandlePoint[];
  indicators?: IndicatorSeries;
  height?: number;
}

export function CandlestickChart({ candles, indicators, height = 320 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const maSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const upperBandRef = useRef<ISeriesApi<"Line"> | null>(null);
  const lowerBandRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: "transparent" },
        textColor: "#CBD5F5"
      },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.2)" },
        horzLines: { color: "rgba(148, 163, 184, 0.2)" }
      }
    });

    const candleSeries = chart.addCandlestickSeries();
    const maSeries = chart.addLineSeries({
      color: "#f97316",
      lineWidth: 2
    });
    const upperBand = chart.addLineSeries({
      color: "#38bdf8",
      lineWidth: 1
    });
    const lowerBand = chart.addLineSeries({
      color: "#38bdf8",
      lineWidth: 1
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    maSeriesRef.current = maSeries;
    upperBandRef.current = upperBand;
    lowerBandRef.current = lowerBand;

    return () => {
      chart.remove();
    };
  }, [height]);

  useEffect(() => {
    if (!candleSeriesRef.current || candles.length === 0) return;

    const candleData: CandlestickData[] = candles.map((c) => ({
      time: c.time as any,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close
    }));

    candleSeriesRef.current.setData(candleData);
    chartRef.current?.timeScale().fitContent();

    if (indicators?.ma && maSeriesRef.current) {
      maSeriesRef.current.setData(indicators.ma);
    }

    if (indicators?.upperBand && upperBandRef.current) {
      upperBandRef.current.setData(indicators.upperBand);
    }
    if (indicators?.lowerBand && lowerBandRef.current) {
      lowerBandRef.current.setData(indicators.lowerBand);
    }
  }, [candles, indicators]);

  return <div ref={containerRef} className="w-full" />;
}