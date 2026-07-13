"use client";

import { ReactNode } from "react";

import * as RadixTooltip from "@radix-ui/react-tooltip";

import { cn } from "@/lib/utils";

export function TooltipProvider({ children }: { children: ReactNode }) {
  return <RadixTooltip.Provider delayDuration={200}>{children}</RadixTooltip.Provider>;
}

export function Tooltip({
  content,
  children,
  className
}: {
  content: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <RadixTooltip.Root>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          sideOffset={6}
          className={cn(
            "z-50 max-w-xs animate-pop-in rounded-lg border bg-surface px-3 py-2 text-xs text-foreground shadow-elevated",
            className
          )}
        >
          {content}
          <RadixTooltip.Arrow className="fill-surface" />
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}
