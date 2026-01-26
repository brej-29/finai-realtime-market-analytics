"use client";

import { useEffect, useState } from "react";

import { AllocationPie } from "../../components/charts/AllocationPie";

interface HoldingRow {
  id: number;
  symbol: string;
  asset_type: string;
  quantity: number;
  average_price: number;
  created_at: string;
}

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<HoldingRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadHoldings() {
      try {
        const apiBase =
          process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
        const resp = await fetch(`${apiBase}/api/v1/holdings`);
        if (!resp.ok) return;
        const data = await resp.json();
        setHoldings(data);
      } catch {
        // ignore for now
      } finally {
        setLoading(false);
      }
    }
    loadHoldings();
  }, []);

  const allocationSlices = holdings.map((h) => ({
    label: h.symbol,
    value: h.quantity * h.average_price
  }));

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Portfolio</h1>
        <p className="text-sm text-slate-400">
          Track your holdings and see your allocation at a glance.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="md:col-span-2 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="text-sm font-semibold text-slate-200">Holdings</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-400">
                  <th className="px-3 py-2 text-left">Symbol</th>
                  <th className="px-3 py-2 text-right">Quantity</th>
                  <th className="px-3 py-2 text-right">Avg Price</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => (
                  <tr key={h.id} className="border-b border-slate-900/40">
                    <td className="px-3 py-2 text-slate-100">{h.symbol}</td>
                    <td className="px-3 py-2 text-right">{h.quantity}</td>
                    <td className="px-3 py-2 text-right">${h.average_price.toFixed(2)}</td>
                  </tr>
                ))}
                {!loading && holdings.length === 0 && (
                  <tr>
                    <td
                      colSpan={3}
                      className="px-3 py-4 text-center text-sm text-slate-500"
                    >
                      No holdings yet. In a future iteration this page will allow adding/editing
                      positions directly.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="text-sm font-semibold text-slate-200">Allocation</h2>
          <div className="mt-3">
            <AllocationPie slices={allocationSlices} />
          </div>
        </div>
      </div>
    </div>
  );
}