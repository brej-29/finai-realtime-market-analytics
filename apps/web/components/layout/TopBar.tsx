"use client";

import { useEffect, useState, type ReactNode } from "react";

import { usePathname } from "next/navigation";
import {
  Activity,
  LayoutDashboard,
  LineChart,
  ScrollText,
  Sparkles,
  Wallet
} from "lucide-react";

import { cn } from "@/lib/utils";

// Kept local (not imported from layout.tsx) so TopBar stays decoupled from the
// sidebar's nav config, per design ticket. Order matters: /symbol/* must be
// checked as a prefix match, same as the other section routes.
const PAGE_CONTEXTS: { match: (path: string) => boolean; label: string; icon: ReactNode }[] = [
  { match: (p) => p === "/", label: "Overview", icon: <LayoutDashboard className="h-3.5 w-3.5" /> },
  { match: (p) => p.startsWith("/watchlist"), label: "Watchlist", icon: <ScrollText className="h-3.5 w-3.5" /> },
  { match: (p) => p.startsWith("/portfolio"), label: "Portfolio", icon: <Wallet className="h-3.5 w-3.5" /> },
  { match: (p) => p.startsWith("/alerts"), label: "Alerts", icon: <LineChart className="h-3.5 w-3.5" /> },
  { match: (p) => p.startsWith("/analytics"), label: "Analytics", icon: <LineChart className="h-3.5 w-3.5" /> },
  { match: (p) => p.startsWith("/research"), label: "Research", icon: <Sparkles className="h-3.5 w-3.5" /> },
  { match: (p) => p.startsWith("/symbol"), label: "Symbol detail", icon: <Activity className="h-3.5 w-3.5" /> }
];

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.host}`;
  }
  return "http://localhost:8000";
}

const HEALTH_POLL_INTERVAL_MS = 60_000;

export function TopBar() {
  const pathname = usePathname();
  const [apiHealthy, setApiHealthy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const apiBase = getApiBase();

    async function checkHealth() {
      try {
        const resp = await fetch(`${apiBase}/health`);
        if (!cancelled) setApiHealthy(resp.ok);
      } catch {
        if (!cancelled) setApiHealthy(false);
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, HEALTH_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const context = PAGE_CONTEXTS.find((entry) => entry.match(pathname ?? ""));

  return (
    <div className="flex flex-1 items-center gap-3">
      <div className="hidden items-center gap-2.5 md:flex">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/[0.04] text-brand-light">
          {context ? context.icon : <Sparkles className="h-3.5 w-3.5" />}
        </span>
        <span className="font-display text-sm font-medium text-foreground">
          {context ? context.label : "FinAI"}
        </span>
      </div>

      <span
        className={cn(
          "ml-auto inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
          apiHealthy
            ? "border-positive/30 bg-positive/10 text-positive"
            : "border-negative/30 bg-negative/10 text-negative"
        )}
      >
        <span className="relative flex h-1.5 w-1.5">
          <span
            className={cn(
              "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
              apiHealthy ? "bg-positive" : "bg-negative"
            )}
          />
          <span
            className={cn("relative inline-flex h-1.5 w-1.5 rounded-full", apiHealthy ? "bg-positive" : "bg-negative")}
          />
        </span>
        <span className="hidden sm:inline">{apiHealthy ? "API healthy" : "API unreachable"}</span>
      </span>
    </div>
  );
}
