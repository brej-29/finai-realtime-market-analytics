import { render, screen } from "@testing-library/react";
import React from "react";
import { vi } from "vitest";

vi.mock("../hooks/useRealtimePrices", () => ({
  useRealtimePrices: () => ({
    status: "connected",
    ticks: {}
  })
}));

// Mock store, though symbol page only uses realtime hook today
vi.mock("../store/useAppStore", () => ({
  useAppStore: () => ({
    serverStatus: { apiHealthy: true, lastChecked: "2024-01-01T00:00:00Z" },
    setServerStatus: vi.fn()
  })
}));

(global as any).fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () =>
      Promise.resolve({
        bars: [],
        items: [],
        technical_summary: {
          rsi: null,
          rsi_label: null,
          macd: null,
          macd_signal: null,
          macd_histogram: null,
          macd_label: null
        },
        forecast_summary: null,
        anomalies: [],
        disclaimer: ""
      })
  })
);

import SymbolDetailPage from "../app/symbol/[symbol]/page";

describe("SymbolDetailPage", () => {
  it("renders symbol header", () => {
    render(<SymbolDetailPage params={{ symbol: "AAPL" }} />);
    expect(screen.getByText(/AAPL/i)).toBeInTheDocument();
  });
});