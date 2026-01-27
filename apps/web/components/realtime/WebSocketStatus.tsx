"use client";

import React from "react";

type Status = "connected" | "connecting" | "disconnected";

interface Props {
  status: Status;
}

const statusConfig: Record<
  Status,
  { label: string; className: string }
> = {
  connected: {
    label: "Live",
    className: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
  },
  connecting: {
    label: "Connecting",
    className: "bg-amber-500/10 text-amber-300 border-amber-500/40"
  },
  disconnected: {
    label: "Offline",
    className: "bg-red-500/10 text-red-300 border-red-500/40"
  }
};

export function WebSocketStatus({ status }: Props) {
  const cfg = statusConfig[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${cfg.className}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {cfg.label}
    </span>
  );
}