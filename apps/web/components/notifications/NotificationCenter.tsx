"use client";

import { useEffect, useState } from "react";

import { useAppStore } from "../../store/useAppStore";

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
  const { alertEvents, unreadAlertCount, setAlertEvents, addAlertEvent, markAllAlertsRead } =
    useAppStore();
  const [open, setOpen] = useState(false);

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
    markAllAlertsRead();
  }, [open, alertEvents.length, markAllAlertsRead]);

  function toggleOpen() {
    setOpen((prev) => !prev);
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={toggleOpen}
        className="relative rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1 text-xs font-medium text-slate-200 hover:border-brand-light"
      >
        🔔
        {unreadAlertCount > 0 && (
          <span className="absolute -right-1 -top-1 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-brand text-[10px] text-slate-900">
            {unreadAlertCount > 9 ? "9+" : unreadAlertCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-2 w-80 rounded-md border border-slate-800 bg-slate-900/95 p-3 text-xs shadow-lg">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-semibold text-slate-100">Alerts</span>
            <span className="text-[10px] uppercase tracking-wide text-slate-500">
              In-app notifications
            </span>
          </div>
          <div className="max-h-64 space-y-2 overflow-y-auto">
            {alertEvents.length === 0 && (
              <p className="text-slate-500">No alert events yet. Create price or RSI alerts to see them here.</p>
            )}
            {alertEvents.map((event) => (
              <div
                key={event.id}
                className={`rounded-md border px-2 py-1 ${
                  event.read ? "border-slate-800 bg-slate-900" : "border-brand/40 bg-brand/5"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-100">{event.symbol}</span>
                  <span className="text-[10px] text-slate-500">
                    {new Date(event.ts).toLocaleTimeString()}
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-slate-200">{event.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}