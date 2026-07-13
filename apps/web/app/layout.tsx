import "@/app/globals.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";

import { Toaster } from "sonner";
import {
  LayoutDashboard,
  LineChart,
  ScrollText,
  Sparkles,
  Wallet
} from "lucide-react";

import { MobileNav } from "@/components/layout/MobileNav";
import { NavLink } from "@/components/layout/NavLink";
import { NotificationCenter } from "@/components/notifications/NotificationCenter";
import { TooltipProvider } from "@/components/ui/Tooltip";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "FinAI Realtime Market Analytics",
  description: "Realtime stock & crypto analytics dashboard"
};

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: <LayoutDashboard className="h-3.5 w-3.5" /> },
  { href: "/watchlist", label: "Watchlist", icon: <ScrollText className="h-3.5 w-3.5" /> },
  { href: "/portfolio", label: "Portfolio", icon: <Wallet className="h-3.5 w-3.5" /> },
  { href: "/alerts", label: "Alerts", icon: <LineChart className="h-3.5 w-3.5" /> },
  { href: "/analytics", label: "Analytics", icon: <LineChart className="h-3.5 w-3.5" /> },
  { href: "/research", label: "Research", icon: <Sparkles className="h-3.5 w-3.5" /> }
];

export default function RootLayout(props: { children: React.ReactNode }) {
  const { children } = props;
  return (
    <html lang="en" className={inter.variable}>
      <body className="app-shell font-sans">
        <TooltipProvider>
          <header className="sticky top-0 z-30 border-b bg-background/80 backdrop-blur-lg">
            <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 md:px-6">
              <Link href="/" className="flex items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-light to-brand text-sm font-bold text-slate-950 shadow-glow">
                  F
                </span>
                <div className="hidden sm:block">
                  <p className="text-sm font-semibold leading-tight text-foreground">
                    FinAI Realtime Analytics
                  </p>
                  <p className="text-[11px] leading-tight text-muted">Stocks &amp; Crypto</p>
                </div>
              </Link>

              <nav className="hidden items-center gap-0.5 rounded-full border bg-surface/60 p-1 md:flex">
                {NAV_ITEMS.map((item) => (
                  <NavLink
                    key={item.href}
                    href={item.href}
                    label={item.label}
                    icon={item.icon}
                    layoutId="desktop-nav-active"
                  />
                ))}
              </nav>

              <div className="flex items-center gap-2">
                <NotificationCenter />
                <MobileNav />
              </div>
            </div>
          </header>

          <div className="app-main mx-auto w-full max-w-7xl">
            <aside className="app-sidebar hidden md:block">
              <div className="flex h-full flex-col gap-1 px-3 py-6">
                <p className="mb-2 px-3 text-[11px] font-medium uppercase tracking-wide text-muted">
                  Navigation
                </p>
                {NAV_ITEMS.map((item) => (
                  <NavLink
                    key={item.href}
                    href={item.href}
                    label={item.label}
                    icon={item.icon}
                    layoutId="sidebar-nav-active"
                    variant="row"
                  />
                ))}
              </div>
            </aside>
            <main className="app-content">{children}</main>
          </div>
        </TooltipProvider>
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "rgb(15 18 22)",
              border: "1px solid rgb(255 255 255 / 0.08)",
              color: "rgb(250 250 250)"
            }
          }}
        />
      </body>
    </html>
  );
}
