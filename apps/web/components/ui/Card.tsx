"use client";

import { HTMLAttributes, forwardRef, useRef, type PointerEvent as ReactPointerEvent } from "react";

import { cn } from "@/lib/utils";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Adds a mouse-tracked radial glow that follows the cursor on hover. */
  spotlight?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, spotlight = false, onPointerMove, ...props }, ref) => {
    const localRef = useRef<HTMLDivElement | null>(null);

    function handlePointerMove(e: ReactPointerEvent<HTMLDivElement>) {
      onPointerMove?.(e);
      if (!spotlight || !localRef.current) return;
      const rect = localRef.current.getBoundingClientRect();
      localRef.current.style.setProperty("--spotlight-x", `${e.clientX - rect.left}px`);
      localRef.current.style.setProperty("--spotlight-y", `${e.clientY - rect.top}px`);
    }

    return (
      <div
        ref={(node) => {
          localRef.current = node;
          if (typeof ref === "function") ref(node);
          else if (ref) ref.current = node;
        }}
        onPointerMove={handlePointerMove}
        className={cn(
          "rounded-2xl border bg-surface/70 shadow-soft backdrop-blur-sm",
          spotlight && "spotlight-card",
          className
        )}
        {...props}
      />
    );
  }
);
Card.displayName = "Card";

export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-1 p-4 pb-0 sm:p-5 sm:pb-0", className)} {...props} />
  )
);
CardHeader.displayName = "CardHeader";

export const CardTitle = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <h2
      ref={ref}
      className={cn("text-sm font-semibold text-foreground", className)}
      {...props}
    />
  )
);
CardTitle.displayName = "CardTitle";

export const CardDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn("text-xs text-muted", className)} {...props} />
  )
);
CardDescription.displayName = "CardDescription";

export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-4 sm:p-5", className)} {...props} />
  )
);
CardContent.displayName = "CardContent";
