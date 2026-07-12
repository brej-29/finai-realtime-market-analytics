import { render, screen } from "@testing-library/react";
import React from "react";
import { vi } from "vitest";

vi.mock("../hooks/useRealtimePrices", () => ({
  useRealtimePrices: () => ({
    status: "connected",
    ticks: {}
  })
}));

// The page reads ?asset_type= via next/navigation, which needs a router
// context that plain RTL rendering doesn't provide.
const searchParamsGet = vi.fn<[string], string | null>(() => null);
vi.mock("next/navigation", () => ({
  useSearchParams: () => ({ get: searchParamsGet })
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
  it("renders symbol header with stock badge by default", () => {
    searchParamsGet.mockReturnValue(null);
    render(<SymbolDetailPage params={{ symbol: "AAPL" }} />);
    expect(screen.getByText(/AAPL/i)).toBeInTheDocument();
    expect(screen.getByText("stock")).toBeInTheDocument();
  });

  it("renders crypto badge when asset_type=crypto is passed", () => {
    searchParamsGet.mockImplementation((key) => (key === "asset_type" ? "crypto" : null));
    render(<SymbolDetailPage params={{ symbol: "BTC" }} />);
    expect(screen.getByText(/BTC/i)).toBeInTheDocument();
    expect(screen.getByText("crypto")).toBeInTheDocument();
  });
});