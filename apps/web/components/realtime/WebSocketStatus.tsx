"use client";

import { Wifi, WifiOff } from "lucide-react";
import { motion } from "motion/react";

import { cn } from "@/lib/utils";

type Status = "connected" | "connecting" | "disconnected";

interface Props {
  status: Status;
}

const statusConfig: Record<Status, { label: string; className: string }> = {
  connected: {
    label: "Live",
    className: "border-positive/30 bg-positive/10 text-positive"
  },
  connecting: {
    label: "Connecting",
    className: "border-warning/30 bg-warning/10 text-warning"
  },
  disconnected: {
    label: "Offline",
    className: "border-negative/30 bg-negative/10 text-negative"
  }
};

export function WebSocketStatus({ status }: Props) {
  const cfg = statusConfig[status];
  const Icon = status === "disconnected" ? WifiOff : Wifi;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        cfg.className
      )}
    >
      <span className="relative flex h-1.5 w-1.5">
        {status === "connected" && (
          <motion.span
            className="absolute inline-flex h-full w-full rounded-full bg-positive"
            animate={{ scale: [1, 1.8, 1.8], opacity: [0.8, 0, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeOut" }}
          />
        )}
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
      </span>
      <Icon className="h-3 w-3" />
      {cfg.label}
    </span>
  );
}
