import "@/app/globals.css";
import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import Link from "next/link";

import { Toaster } from "sonner";
import {
  LayoutDashboard,
  LineChart,
  ScrollText,
  Sparkles,
  Wallet
} from "lucide-react";

import { AmbientBackground } from "@/components/layout/AmbientBackground";
import { MobileNav } from "@/components/layout/MobileNav";
import { NavLink } from "@/components/layout/NavLink";
import { NotificationCenter } from "@/components/notifications/NotificationCenter";
import { MotionProvider } from "@/components/providers/MotionProvider";
import { TooltipProvider } from "@/components/ui/Tooltip";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const spaceGrotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-space-grotesk" });
const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-mono" });

export const metadata: Metadata = {
  // TODO: update metadataBase once the production domain is finalized after deployment.
  metadataBase: new URL("https://finai-analytics.example.com"),
  title: {
    default: "FinAI Realtime Market Analytics",
    template: "%s · FinAI"
  },
  description:
    "Realtime stock and crypto analytics dashboard with a multi-agent AI research desk for market insights.",
  openGraph: {
    title: "FinAI Realtime Market Analytics",
    description:
      "Realtime stock and crypto analytics dashboard with a multi-agent AI research desk for market insights.",
    type: "website",
    siteName: "FinAI Realtime Market Analytics"
  },
  twitter: {
    card: "summary"
  }
};

export const viewport: Viewport = {
  themeColor: "#06080B"
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
    <html lang="en" className={cn(inter.variable, spaceGrotesk.variable, jetbrainsMono.variable)}>
      <body className="min-h-screen font-sans">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-brand focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-slate-950"
        >
          Skip to content
        </a>
        <AmbientBackground />
        <MotionProvider>
        <TooltipProvider>
          <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-white/[0.06] bg-surface/30 backdrop-blur-xl md:flex">
            <Link href="/" className="flex items-center gap-2.5 px-5 py-5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-light to-brand text-sm font-bold text-slate-950 shadow-glow">
                F
              </span>
              <div>
                <p className="font-display text-sm font-semibold leading-tight text-foreground">
                  FinAI Realtime Analytics
                </p>
                <p className="text-[11px] leading-tight text-muted">Stocks &amp; Crypto</p>
              </div>
            </Link>

            <nav className="flex flex-1 flex-col gap-1 px-3 py-2">
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
            </nav>

            <div className="flex items-center gap-2 border-t border-white/[0.06] px-5 py-4">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-brand" />
              </span>
              <p className="text-[11px] text-muted">FinAI · Phase 2</p>
            </div>
          </aside>

          <div className="flex min-h-screen flex-col md:pl-64">
            <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-4 border-b border-white/[0.06] bg-background/60 px-4 backdrop-blur-xl md:justify-end md:px-8">
              <Link href="/" className="flex items-center gap-2.5 md:hidden">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-light to-brand text-sm font-bold text-slate-950 shadow-glow">
                  F
                </span>
                <p className="font-display text-sm font-semibold leading-tight text-foreground">
                  FinAI
                </p>
              </Link>

              <div className="flex items-center gap-2">
                <NotificationCenter />
                <MobileNav />
              </div>
            </header>

            <main id="main-content" className="flex-1 p-5 md:p-8">{children}</main>
          </div>
        </TooltipProvider>
        </MotionProvider>
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
