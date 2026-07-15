"use client";

import { motion } from "motion/react";

import { cn, formatCurrency } from "@/lib/utils";

export interface DonutSlice {
  label: string;
  value: number;
  color: string;
}

const RADIUS = 40;
const STROKE = 13;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function DonutChart({
  slices,
  totalLabel = "Total",
  className
}: {
  slices: DonutSlice[];
  totalLabel?: string;
  className?: string;
}) {
  const total = slices.reduce((sum, s) => sum + s.value, 0);

  if (!slices.length || total <= 0) {
    return (
      <div className={cn("flex aspect-square items-center justify-center rounded-full border border-dashed border-border text-xs text-muted", className)}>
        No data yet
      </div>
    );
  }

  let cumulative = 0;

  return (
    <div className={cn("flex flex-col items-center gap-4 sm:flex-row sm:items-center", className)}>
      <div className="relative aspect-square w-40 shrink-0">
        <svg viewBox="0 0 100 100" className="-rotate-90">
          <circle
            cx="50"
            cy="50"
            r={RADIUS}
            fill="none"
            stroke="rgb(var(--surface-hover))"
            strokeWidth={STROKE}
          />
          {slices.map((slice, i) => {
            const fraction = slice.value / total;
            const dash = fraction * CIRCUMFERENCE;
            const offset = -(cumulative * CIRCUMFERENCE);
            cumulative += fraction;
            return (
              <motion.circle
                key={slice.label}
                cx="50"
                cy="50"
                r={RADIUS}
                fill="none"
                stroke={slice.color}
                strokeWidth={STROKE}
                strokeLinecap="round"
                initial={{ strokeDasharray: `0 ${CIRCUMFERENCE}` }}
                animate={{ strokeDasharray: `${dash} ${CIRCUMFERENCE - dash}` }}
                style={{ strokeDashoffset: offset }}
                transition={{ duration: 0.8, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
              />
            );
          })}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[10px] uppercase tracking-wide text-muted">{totalLabel}</span>
          <span className="text-sm font-semibold tabular-nums text-foreground">
            {formatCurrency(total)}
          </span>
        </div>
      </div>
      <div className="flex min-w-0 flex-1 flex-col justify-center gap-3">
        {slices.map((slice, i) => {
          const pct = (slice.value / total) * 100;
          return (
            <div key={slice.label} className="flex min-w-0 items-center gap-2.5 text-xs">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: slice.color }}
              />
              <span className="shrink-0 capitalize text-muted">{slice.label}</span>
              <div className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: slice.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.8, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
                />
              </div>
              <span className="shrink-0 whitespace-nowrap text-right tabular-nums text-foreground">
                {formatCurrency(slice.value)}
                <span className="ml-1.5 text-muted">{pct.toFixed(0)}%</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
