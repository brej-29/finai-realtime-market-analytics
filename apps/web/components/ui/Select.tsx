import { SelectHTMLAttributes, forwardRef } from "react";

import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <div className="relative inline-flex">
      <select
        ref={ref}
        className={cn(
          "h-10 appearance-none rounded-xl border bg-surface pl-3 pr-8 text-sm text-foreground",
          "transition-colors hover:border-border-hover/20 focus:border-brand/50",
          className
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
    </div>
  )
);
Select.displayName = "Select";
