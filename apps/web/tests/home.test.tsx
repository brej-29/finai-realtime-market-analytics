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
    setServerStatus: vi.fn()
  })
}));

import HomePage from "../app/page";

describe("HomePage", () => {
  it("renders API health status", () => {
    render(<HomePage />);
    expect(screen.getByText(/API healthy/i)).toBeInTheDocument();
  });
});