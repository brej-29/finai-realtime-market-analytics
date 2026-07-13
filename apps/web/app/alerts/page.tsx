"use client";

import { FormEvent, useEffect, useState } from "react";

import { motion } from "motion/react";
import { Bell, TrendingDown, TrendingUp } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { formatCurrency } from "@/lib/utils";

interface AlertRow {
  id: number;
  symbol: string;
  asset_type: string;
  direction: string;
  threshold: number;
  is_active: boolean;
  created_at: string;
}

const DIRECTION_LABELS: Record<string, string> = {
  price_above: "Price above",
  price_below: "Price below",
  rsi_above: "RSI above",
  rsi_below: "RSI below",
  ma_cross: "MA cross"
};

function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [symbol, setSymbol] = useState("");
  const [assetType, setAssetType] = useState<"stock" | "crypto">("stock");
  const [direction, setDirection] = useState<"price_above" | "price_below">("price_above");
  const [threshold, setThreshold] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    async function loadAlerts() {
      try {
        const resp = await fetch(`${getApiBase()}/api/v1/alerts`);
        if (!resp.ok) return;
        setAlerts(await resp.json());
      } catch {
        // ignore for now
      } finally {
        setLoaded(true);
      }
    }
    loadAlerts();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!symbol.trim() || !threshold || submitting) return;
    setSubmitting(true);
    try {
      const resp = await fetch(`${getApiBase()}/api/v1/alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: symbol.trim().toUpperCase(),
          asset_type: assetType,
          direction,
          threshold: parseFloat(threshold)
        })
      });
      if (resp.ok) {
        const created = await resp.json();
        setAlerts([created, ...alerts]);
        setSymbol("");
        setThreshold("");
        toast.success(`Alert created for ${created.symbol}`);
      } else {
        toast.error("Could not create alert. Please try again.");
      }
    } catch {
      toast.error("Could not reach the API. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-4xl space-y-6"
    >
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">Price Alerts</h1>
        <p className="text-sm text-muted">Define price, RSI, or MA-cross alerts for your symbols.</p>
      </div>

      <Card className="p-4">
        <form onSubmit={handleCreate} className="flex flex-wrap gap-2.5">
          <Input
            type="text"
            placeholder="Symbol (e.g. AAPL)"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="min-w-[140px] flex-1"
          />
          <Select
            value={assetType}
            onChange={(e) => setAssetType(e.target.value as "stock" | "crypto")}
            aria-label="Asset type"
          >
            <option value="stock">Stock</option>
            <option value="crypto">Crypto</option>
          </Select>
          <Select value={direction} onChange={(e) => setDirection(e.target.value as any)} aria-label="Condition">
            <option value="price_above">Price above</option>
            <option value="price_below">Price below</option>
          </Select>
          <Input
            type="number"
            placeholder="Threshold"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            className="w-28"
          />
          <Button type="submit" disabled={submitting || !symbol.trim() || !threshold}>
            {submitting ? "Creating…" : "Create alert"}
          </Button>
        </form>
      </Card>

      <Card className="overflow-hidden p-0">
        {loaded && alerts.length === 0 ? (
          <EmptyState
            icon={<Bell className="h-5 w-5" />}
            title="No alerts yet"
            description="Create an alert above to get notified on key price or indicator levels."
            className="border-none"
          />
        ) : (
          <table className="min-w-full text-sm">
            <thead className="bg-surface-hover/40 text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2.5 text-left">Symbol</th>
                <th className="px-4 py-2.5 text-left">Type</th>
                <th className="px-4 py-2.5 text-left">Condition</th>
                <th className="px-4 py-2.5 text-right">Threshold</th>
                <th className="px-4 py-2.5 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {alerts.map((a) => (
                <tr key={a.id} className="hover:bg-surface-hover/60">
                  <td className="px-4 py-2.5 font-medium text-foreground">{a.symbol}</td>
                  <td className="px-4 py-2.5 text-xs uppercase text-muted">{a.asset_type}</td>
                  <td className="px-4 py-2.5 text-muted">
                    <span className="inline-flex items-center gap-1.5">
                      {a.direction.includes("below") ? (
                        <TrendingDown className="h-3.5 w-3.5 text-negative" />
                      ) : (
                        <TrendingUp className="h-3.5 w-3.5 text-positive" />
                      )}
                      {DIRECTION_LABELS[a.direction] ?? a.direction}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-foreground">
                    {formatCurrency(a.threshold)}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <Badge variant={a.is_active ? "positive" : "default"}>
                      {a.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </motion.div>
  );
}
