import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { cn } from "@/lib/utils";

export function PriceDelta({
  value,
  suffix = "%",
  className
}: {
  value: number | null | undefined;
  suffix?: string;
  className?: string;
}) {
  if (value == null || Number.isNaN(value)) {
    return <span className={cn("inline-flex items-center gap-0.5 text-xs text-muted", className)}>—</span>;
  }

  const isFlat = Math.abs(value) < 0.005;
  const isPositive = value > 0;
  const Icon = isFlat ? Minus : isPositive ? ArrowUpRight : ArrowDownRight;
  const tone = isFlat ? "text-muted" : isPositive ? "text-positive" : "text-negative";

  return (
    <span className={cn("inline-flex items-center gap-0.5 text-xs font-medium tabular-nums", tone, className)}>
      <Icon className="h-3 w-3" />
      {isPositive && !isFlat ? "+" : ""}
      {value.toFixed(2)}
      {suffix}
    </span>
  );
}
