"use client";

import { useEffect, useRef, useState } from "react";

import { AnimatePresence, motion } from "motion/react";
import { Bell } from "lucide-react";

import { useAppStore } from "@/store/useAppStore";
import { relativeTime } from "@/lib/utils";

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.host}`;
  }
  return "http://localhost:8000";
}

export function NotificationCenter() {
  const { alertEvents, unreadAlertCount, setAlertEvents, markAllAlertsRead } = useAppStore();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    async function loadEvents() {
      try {
        const apiBase = getApiBase();
        const resp = await fetch(`${apiBase}/api/v1/alerts/events?limit=20`);
        if (!resp.ok) return;
        const data = await resp.json();
        const events = (data || []).map((e: any) => ({
          id: e.id,
          alertId: e.alert_id,
          symbol: e.symbol,
          assetType: e.asset_type,
          message: e.message,
          ts: e.fired_at,
          status: e.status,
          payload: e.payload,
          read: false
        }));
        setAlertEvents(events);
      } catch {
        // ignore errors; notification center is best-effort
      }
    }

    loadEvents();
  }, [setAlertEvents]);

  useEffect(() => {
    if (!open || alertEvents.length === 0) return;
    const timer = setTimeout(markAllAlertsRead, 600);
    return () => clearTimeout(timer);
  }, [open, alertEvents.length, markAllAlertsRead]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label="Notifications"
        className="relative flex h-9 w-9 items-center justify-center rounded-full border bg-surface text-muted transition-colors hover:text-foreground"
      >
        <Bell className="h-4 w-4" />
        <AnimatePresence>
          {unreadAlertCount > 0 && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
              className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-brand px-1 text-[10px] font-semibold text-slate-950"
            >
              {unreadAlertCount > 9 ? "9+" : unreadAlertCount}
            </motion.span>
          )}
        </AnimatePresence>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="absolute right-0 z-40 mt-2 w-80 rounded-2xl border bg-surface/95 p-3 text-xs shadow-elevated backdrop-blur-lg"
          >
            <div className="mb-2 flex items-center justify-between px-1">
              <span className="text-sm font-semibold text-foreground">Alerts</span>
              <span className="text-[10px] uppercase tracking-wide text-muted">
                {alertEvents.length} recent
              </span>
            </div>
            <div className="max-h-72 space-y-1.5 overflow-y-auto">
              {alertEvents.length === 0 && (
                <p className="px-1 py-6 text-center text-muted">
                  No alert events yet. Create a price or RSI alert to see them here.
                </p>
              )}
              {alertEvents.map((event) => (
                <div
                  key={event.id}
                  className={`rounded-xl border px-2.5 py-2 transition-colors ${
                    event.read
                      ? "border-transparent bg-transparent"
                      : "border-brand/30 bg-brand/5"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground">{event.symbol}</span>
                    <span className="text-[10px] text-muted">{relativeTime(event.ts)}</span>
                  </div>
                  <p className="mt-0.5 text-[11px] text-muted">{event.message}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
