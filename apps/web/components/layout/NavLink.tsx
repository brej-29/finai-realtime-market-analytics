"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { motion } from "motion/react";

import { cn } from "@/lib/utils";

interface Props {
  href: string;
  label: string;
  icon: React.ReactNode;
  layoutId: string;
  onNavigate?: () => void;
  variant?: "pill" | "row";
}

export function NavLink({ href, label, icon, layoutId, onNavigate, variant = "pill" }: Props) {
  const pathname = usePathname();
  const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);

  if (variant === "row") {
    return (
      <Link
        href={href}
        onClick={onNavigate}
        className={cn(
          "relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors duration-200",
          isActive
            ? "bg-white/[0.06] text-foreground shadow-[0_0_0_1px_rgb(20_184_166_/_0.12)]"
            : "text-muted hover:bg-white/[0.04] hover:text-foreground"
        )}
      >
        {isActive && (
          <motion.span
            layoutId={layoutId}
            className="absolute inset-y-1 left-0 w-0.5 rounded-full bg-brand shadow-glow"
            transition={{ type: "spring", stiffness: 400, damping: 32 }}
          />
        )}
        <span className={cn("relative z-10", isActive && "text-brand-light")}>{icon}</span>
        <span className="relative z-10">{label}</span>
      </Link>
    );
  }

  return (
    <Link
      href={href}
      onClick={onNavigate}
      className={cn(
        "relative flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors",
        isActive ? "text-foreground" : "text-muted hover:text-foreground"
      )}
    >
      {isActive && (
        <motion.span
          layoutId={layoutId}
          className="absolute inset-0 rounded-full bg-surface-hover"
          transition={{ type: "spring", stiffness: 400, damping: 32 }}
        />
      )}
      <span className="relative z-10 flex items-center gap-1.5">
        {icon}
        {label}
      </span>
    </Link>
  );
}
