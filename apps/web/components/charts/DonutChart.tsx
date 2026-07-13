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
      <div className="flex w-full flex-col gap-2">
        {slices.map((slice) => (
          <div key={slice.label} className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-2 text-muted">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: slice.color }}
              />
              {slice.label}
            </span>
            <span className="tabular-nums text-foreground">
              {formatCurrency(slice.value)}
              <span className="ml-1.5 text-muted">
                {((slice.value / total) * 100).toFixed(0)}%
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
