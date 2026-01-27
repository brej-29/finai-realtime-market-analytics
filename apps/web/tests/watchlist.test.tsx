import { render, screen } from "@testing-library/react";
import React from "react";
import { vi } from "vitest";

vi.mock("../hooks/useRealtimePrices", () => ({
  useRealtimePrices: () => ({
    status: "connected",
    ticks: {}
  })
}));

vi.mock("../store/useAppStore", () => ({
  useAppStore: () => ({
    serverStatus: { apiHealthy: true, lastChecked: "2024-01-01T00:00:00Z" },
    watchlistItems: [],
    setWatchlistItems: vi.fn(),
    holdings: [],
    setHoldings: vi.fn(),
    alerts: [],
    setAlerts: vi.fn(),
    latestTicks: {},
    updateTick: vi.fn(),
    alertEvents: [],
    unreadAlertCount: 0,
    setAlertEvents: vi.fn(),
    addAlertEvent: vi.fn(),
    markAllAlertsRead: vi.fn()
  })
}));

// Minimal fetch mock for watchlist loading
(global as any).fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ items: [] })
  })
);

import WatchlistPage from "../app/watchlist/page";

describe("WatchlistPage", () => {
  it("renders heading", () => {
    render(<WatchlistPage />);
    expect(screen.getByText(/Watchlist/i)).toBeInTheDocument();
  });
});