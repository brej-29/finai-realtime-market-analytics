import { InputHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 rounded-xl border bg-surface px-3 text-sm text-foreground placeholder:text-muted/70",
        "transition-colors hover:border-border-hover/20 focus:border-brand/50",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
