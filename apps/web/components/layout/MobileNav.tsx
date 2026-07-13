"use client";

import { useState } from "react";

import { Drawer } from "vaul";
import { LayoutDashboard, LineChart, Menu, ScrollText, Sparkles, Wallet, X } from "lucide-react";

import { NavLink } from "@/components/layout/NavLink";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: <LayoutDashboard className="h-4 w-4" /> },
  { href: "/watchlist", label: "Watchlist", icon: <ScrollText className="h-4 w-4" /> },
  { href: "/portfolio", label: "Portfolio", icon: <Wallet className="h-4 w-4" /> },
  { href: "/alerts", label: "Alerts", icon: <LineChart className="h-4 w-4" /> },
  { href: "/analytics", label: "Analytics", icon: <LineChart className="h-4 w-4" /> },
  { href: "/research", label: "Research", icon: <Sparkles className="h-4 w-4" /> }
];

export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <Drawer.Root open={open} onOpenChange={setOpen} direction="right">
      <Drawer.Trigger asChild>
        <button
          type="button"
          aria-label="Open navigation menu"
          className="flex h-9 w-9 items-center justify-center rounded-full border bg-surface text-muted transition-colors hover:text-foreground md:hidden"
        >
          <Menu className="h-4 w-4" />
        </button>
      </Drawer.Trigger>
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
        <Drawer.Content className="fixed inset-y-0 right-0 z-50 flex h-full w-72 flex-col gap-1 border-l bg-background p-4 outline-none">
          <div className="mb-2 flex items-center justify-between">
            <Drawer.Title className="text-sm font-semibold text-foreground">Navigate</Drawer.Title>
            <Drawer.Close asChild>
              <button
                type="button"
                aria-label="Close navigation menu"
                className="flex h-8 w-8 items-center justify-center rounded-full text-muted hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </Drawer.Close>
          </div>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.href}
              href={item.href}
              label={item.label}
              icon={item.icon}
              layoutId="mobile-nav-active"
              variant="row"
              onNavigate={() => setOpen(false)}
            />
          ))}
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
