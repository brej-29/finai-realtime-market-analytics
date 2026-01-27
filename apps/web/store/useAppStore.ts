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
  direction: "price_above" | "price_below" | "rsi_above" | "rsi_below" | "ma_cross";
  threshold: number;
}

export interface AlertEvent {
  id: number;
  alertId: number;
  symbol: string;
  assetType: AssetType;
  message: string;
  ts: string;
  status: "new" | "delivered" | "error";
  payload?: Record<string, unknown>;
  read?: boolean;
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
  alertEvents: AlertEvent[];
  unreadAlertCount: number;

  setServerStatus(status: ServerStatus): void;
  setWatchlistItems(items: WatchlistItem[]): void;
  setHoldings(items: Holding[]): void;
  setAlerts(items: Alert[]): void;
  updateTick(tick: RealtimeTick): void;

  setAlertEvents(events: AlertEvent[]): void;
  addAlertEvent(event: AlertEvent): void;
  markAllAlertsRead(): void;
}

export const useAppStore = create<AppState>((set) => ({
  serverStatus: { apiHealthy: false, lastChecked: null },
  watchlistItems: [],
  holdings: [],
  alerts: [],
  latestTicks: {},
  alertEvents: [],
  unreadAlertCount: 0,

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
  },

  setAlertEvents(events) {
    set({
      alertEvents: events,
      unreadAlertCount: events.filter((e) => !e.read).length
    });
  },

  addAlertEvent(event) {
    set((state) => {
      const nextEvents = [event, ...state.alertEvents];
      const unread = nextEvents.filter((e) => !e.read).length;
      return {
        alertEvents: nextEvents,
        unreadAlertCount: unread
      };
    });
  },

  markAllAlertsRead() {
    set((state) => ({
      alertEvents: state.alertEvents.map((e) => ({ ...e, read: true })),
      unreadAlertCount: 0
    }));
  }
}));