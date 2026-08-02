"use client";

import { useEffect, useRef, useState } from "react";

import { apiFetch } from "@/lib/api";

export type AssetType = "stock" | "crypto";

export type ConnectionStatus = "connected" | "connecting" | "disconnected";

export interface RealtimeTick {
  symbol: string;
  assetType: AssetType;
  price: number;
  ts: string;
  change24h?: number | null;
  isStale?: boolean;
}

interface UseRealtimePricesOptions {
  symbols: string[];
  assetType: AssetType;
}

interface UseRealtimePricesState {
  status: ConnectionStatus;
  ticks: Record<string, RealtimeTick>;
}

/**
 * Hook managing WebSocket connection with auto-reconnect and REST fallback.
 */
export function useRealtimePrices(options: UseRealtimePricesOptions): UseRealtimePricesState {
  const { symbols, assetType } = options;
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [ticks, setTicks] = useState<Record<string, RealtimeTick>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const symbolsRef = useRef(symbols);
  // Key on contents (not array identity) so re-renders with equal symbol lists
  // don't trigger duplicate subscribe messages.
  const symbolsKey = symbols.join(",");

  useEffect(() => {
    symbolsRef.current = symbols;
    // Re-subscribe when the symbol list changes after the socket is already
    // open (e.g. watchlist items load from the API after connect).
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN && symbols.length > 0) {
      ws.send(
        JSON.stringify({
          type: "subscribe",
          symbols,
          assetType
        })
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbolsKey, assetType]);

  useEffect(() => {
    let cancelled = false;

    function getWsUrl(): string | null {
      if (typeof window === "undefined") return null;
      const envUrl = process.env.NEXT_PUBLIC_WS_URL;
      if (envUrl) return envUrl;
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      return `${protocol}://${window.location.host}/ws/stream`;
    }

    async function fetchFallback() {
      try {
        const params = new URLSearchParams();
        symbolsRef.current.forEach((s) => params.append("symbols", s));
        params.set("asset_type", assetType);
        const response = await apiFetch(`/api/v1/quotes?${params.toString()}`);
        if (!response.ok) return;
        const data = await response.json();
        const nextTicks: Record<string, RealtimeTick> = {};
        for (const q of data.quotes ?? []) {
          nextTicks[q.symbol] = {
            symbol: q.symbol,
            assetType: q.asset_type,
            price: q.price,
            ts: q.ts,
            change24h: q.change_24h,
            isStale: q.is_stale
          };
        }
        if (!cancelled) {
          setTicks(nextTicks);
        }
      } catch {
        // swallow; this is a fallback path
      }
    }

    function connect() {
      const url = getWsUrl();
      if (!url) {
        setStatus("disconnected");
        fetchFallback();
        return;
      }

      setStatus("connecting");
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) return;
        setStatus("connected");
        retryRef.current = 0;
        if (symbolsRef.current.length > 0) {
          ws.send(
            JSON.stringify({
              type: "subscribe",
              symbols: symbolsRef.current,
              assetType
            })
          );
        }
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "tick") {
            const tick: RealtimeTick = {
              symbol: msg.symbol,
              assetType: msg.assetType,
              price: msg.price,
              ts: msg.ts,
              change24h: msg.change24h,
              isStale: msg.isStale
            };
            setTicks((prev) => ({ ...prev, [tick.symbol]: tick }));
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (cancelled) return;
        setStatus("disconnected");
        fetchFallback();
        const retry = Math.min(5, retryRef.current + 1);
        retryRef.current = retry;
        const delay = 1000 * retry;
        setTimeout(() => {
          if (!cancelled) {
            connect();
          }
        }, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    const interval = setInterval(() => {
      if (status === "disconnected") {
        fetchFallback();
      }
    }, 15000);

    return () => {
      cancelled = true;
      clearInterval(interval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [assetType]);

  return { status, ticks };
}