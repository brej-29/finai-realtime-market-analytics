"use client";

import { create } from "zustand";

import type { AssetType, RealtimeTick } from "../hooks/useRealtimePrices";

export interface WatchlistItem {
  id: number;
  symbol: string;
  assetType: AssetType;
}

export interface Holding {
  id: number;
  symbol: string;
  assetType: AssetType;
  quantity: number;
  averagePrice: number;
}

export interface Alert {
  id: number;
  symbol: string;
  assetType: AssetType;
  direction: "price_above" | "price_below";
  threshold: number;
}

interface ServerStatus {
  apiHealthy: boolean;
  lastChecked: string | null;
}

interface AppState {
  serverStatus: ServerStatus;
  watchlistItems: WatchlistItem[];
  holdings: Holding[];
  alerts: Alert[];
  latestTicks: Record<string, RealtimeTick>;

  setServerStatus(status: ServerStatus): void;
  setWatchlistItems(items: WatchlistItem[]): void;
  setHoldings(items: Holding[]): void;
  setAlerts(items: Alert[]): void;
  updateTick(tick: RealtimeTick): void;
}

export const useAppStore = create<AppState>((set) => ({
  serverStatus: { apiHealthy: false, lastChecked: null },
  watchlistItems: [],
  holdings: [],
  alerts: [],
  latestTicks: {},

  setServerStatus(status) {
    set({ serverStatus: status });
  },

  setWatchlistItems(items) {
    set({ watchlistItems: items });
  },

  setHoldings(items) {
    set({ holdings: items });
  },

  setAlerts(items) {
    set({ alerts: items });
  },

  updateTick(tick) {
    set((state) => ({
      latestTicks: {
        ...state.latestTicks,
        [tick.symbol]: tick
      }
    }));
  }
}));