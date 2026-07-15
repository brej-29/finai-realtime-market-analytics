"use client";

import { useEffect, useState } from "react";

import Link from "next/link";
import { motion } from "motion/react";
import {
  Activity,
  Bell,
  LineChart,
  ScrollText,
  TrendingDown,
  TrendingUp,
  Wallet
} from "lucide-react";

import { WebSocketStatus } from "@/components/realtime/WebSocketStatus";
import { useRealtimePrices } from "@/hooks/useRealtimePrices";
import { DonutChart } from "@/components/charts/DonutChart";
import { Card, CardContent } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { PriceDelta } from "@/components/ui/PriceDelta";
import { formatCurrency } from "@/lib/utils";

interface PortfolioSummaryByType {
  asset_type: "stock" | "crypto";
  cost_basis: number;
  market_value: number;
  unrealized_pnl: number;
  weight: number | null;
}

interface PortfolioSummary {
  total_cost_basis: number;
  total_market_value: number;
  total_unrealized_pnl: number;
  by_asset_type: Record<string, PortfolioSummaryByType>;
}

const SLICE_COLORS = ["#14B8A6", "#818CF8", "#F97316", "#38BDF8"];

const NEXT_STEPS = [
  {
    href: "/watchlist",
    icon: ScrollText,
    title: "Build your watchlist",
    description: "Track symbols with real-time price updates."
  },
  {
    href: "/portfolio",
    icon: Wallet,
    title: "Add holdings",
    description: "See live P&L and allocation across positions."
  },
  {
    href: "/alerts",
    icon: Bell,
    title: "Set price alerts",
    description: "Get notified on price, RSI, or MA-cross triggers."
  },
  {
    href: "/research",
    icon: LineChart,
    title: "Run AI research",
    description: "Three agents analyze a symbol and write a brief."
  }
];

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } }
};
const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] as const } }
};

export default function HomePage() {
  const { status, ticks } = useRealtimePrices({ symbols: ["AAPL", "MSFT"], assetType: "stock" });
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;

    async function loadSummary() {
      try {
        const resp = await fetch(`${apiBase}/api/v1/portfolio/summary`);
        if (resp.ok) setSummary(await resp.json());
      } catch {
        // API unreachable; empty state below covers this.
      } finally {
        setSummaryLoading(false);
      }
    }

    loadSummary();
  }, []);

  const latestAapl = ticks["AAPL"];
  const hasHoldings = (summary?.total_cost_basis ?? 0) > 0;
  const pnl = summary?.total_unrealized_pnl ?? 0;
  const pnlPct = hasHoldings && summary ? (pnl / summary.total_cost_basis) * 100 : 0;
  const pnlTone = pnl > 0 ? "positive" : pnl < 0 ? "negative" : "neutral";

  const slices = summary
    ? Object.values(summary.by_asset_type).map((entry, i) => ({
        label: entry.asset_type,
        value: entry.market_value,
        color: SLICE_COLORS[i % SLICE_COLORS.length]
      }))
    : [];

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="mx-auto flex max-w-7xl flex-col gap-6"
    >
      <motion.div variants={item} className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">
            Portfolio Overview
          </h1>
          <p className="text-sm text-muted">Real-time insights for your stock &amp; crypto holdings.</p>
        </div>
        <div className="flex items-center gap-3">
          <WebSocketStatus status={status} />
        </div>
      </motion.div>

      <motion.div variants={item} className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Total Market Value"
          value={summary?.total_market_value ?? 0}
          formatter={formatCurrency}
          icon={<Wallet className="h-4 w-4" />}
          loading={summaryLoading}
          helper={
            hasHoldings && summary ? (
              <>Cost basis: {formatCurrency(summary.total_cost_basis)}</>
            ) : (
              <>
                Add holdings in{" "}
                <Link href="/portfolio" className="text-brand-light hover:underline">
                  Portfolio
                </Link>{" "}
                to see live valuations.
              </>
            )
          }
        />
        <StatCard
          label="Unrealized P&L"
          value={pnl}
          formatter={formatCurrency}
          tone={pnlTone}
          icon={pnl < 0 ? <TrendingDown className="h-4 w-4" /> : <TrendingUp className="h-4 w-4" />}
          loading={summaryLoading}
          helper={hasHoldings ? <PriceDelta value={pnlPct} /> : "Live P&L updates as you add holdings."}
        />
        <StatCard
          label="Sample Live Tick"
          value={latestAapl?.price ?? 0}
          formatter={(v) => (latestAapl ? formatCurrency(v) : "—")}
          icon={<Activity className="h-4 w-4" />}
          helper={
            latestAapl ? (
              <span className="flex items-center gap-1.5">
                AAPL <PriceDelta value={latestAapl.change24h} />
              </span>
            ) : (
              "Waiting for live ticks over WebSocket…"
            )
          }
        />
      </motion.div>

      {hasHoldings && summary && (
        <motion.div variants={item}>
          <Card>
            <CardContent className="pt-5">
              <h2 className="mb-4 text-sm font-semibold text-foreground">
                Allocation by asset class
              </h2>
              <DonutChart slices={slices} totalLabel="Portfolio" />
            </CardContent>
          </Card>
        </motion.div>
      )}

      <motion.div variants={item}>
        <h2 className="mb-3 text-sm font-semibold text-foreground">Next steps</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {NEXT_STEPS.map(({ href, icon: Icon, title, description }) => (
            <Link key={href} href={href}>
              <Card className="group h-full transition-colors hover:border-brand/40 hover:bg-surface-hover">
                <CardContent className="flex h-full flex-col gap-2 pt-5">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand/10 text-brand-light transition-transform group-hover:scale-105">
                    <Icon className="h-4 w-4" />
                  </span>
                  <p className="text-sm font-medium text-foreground">{title}</p>
                  <p className="text-xs text-muted">{description}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}
