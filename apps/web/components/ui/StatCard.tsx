"use client";

import { ReactNode } from "react";

import { motion } from "motion/react";

import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: number;
  formatter?: (value: number) => string;
  icon?: ReactNode;
  helper?: ReactNode;
  tone?: "neutral" | "positive" | "negative";
  loading?: boolean;
}

const toneClasses: Record<NonNullable<Props["tone"]>, string> = {
  neutral: "text-foreground",
  positive: "text-positive",
  negative: "text-negative"
};

export function StatCard({ label, value, formatter, icon, helper, tone = "neutral", loading }: Props) {
  return (
    <Card spotlight className="group relative overflow-hidden p-4 transition-colors hover:border-border-hover/20 sm:p-5">
      <div
        className="pointer-events-none absolute -right-8 -top-8 h-28 w-28 rounded-full bg-brand/10 blur-2xl"
        aria-hidden="true"
      />
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
        {icon && (
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-brand/25 to-brand/5 text-brand-light ring-1 ring-brand/25">
            {icon}
          </span>
        )}
      </div>
      <p className={cn("relative mt-3 text-2xl font-semibold tabular-nums", toneClasses[tone])}>
        {loading ? (
          <span className="inline-block h-7 w-24 animate-pulse rounded bg-surface-hover align-middle" />
        ) : (
          <AnimatedNumber value={value} formatter={formatter} />
        )}
      </p>
      {helper && <div className="relative mt-1.5 text-xs text-muted">{helper}</div>}
      <motion.div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-brand/60 to-transparent opacity-0 group-hover:opacity-100"
        transition={{ duration: 0.2 }}
      />
    </Card>
  );
}
