import "../app/globals.css";
import type { Metadata } from "next";
import Link from "next/link";

import { NotificationCenter } from "../components/notifications/NotificationCenter";

export const metadata: Metadata = {
  title: "FinAI Realtime Market Analytics",
  description: "Realtime stock &amp; crypto analytics dashboard"
};

export default function RootLayout(props: { children: React.ReactNode }) {
  const { children } = props;
  return (
    <html lang="en">
      <body className="app-shell">
        <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="h-8 w-8 rounded bg-brand flex items-center justify-center text-xl font-bold">
                F
              </span>
              <div>
                <p className="text-sm font-semibold">FinAI Realtime Analytics</p>
                <p className="text-xs text-slate-400">Stocks &amp; Crypto</p>
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm text-slate-300">
              <nav className="flex items-center gap-4">
                <Link href="/">Home</Link>
                <Link href="/watchlist">Watchlist</Link>
                <Link href="/portfolio">Portfolio</Link>
                <Link href="/alerts">Alerts</Link>
                <Link href="/analytics">Analytics</Link>
                <Link href="/research">Research</Link>
              </nav>
              <NotificationCenter />
            </div>
          </div>
        </header>
        <div className="app-main">
          <aside className="app-sidebar hidden md:block">
            <div className="mx-auto flex h-full max-w-7xl flex-col gap-4 px-4 py-6 text-sm text-slate-300">
              <p className="uppercase tracking-wide text-xs text-slate-500">Navigation</p>
              <Link href="/" className="hover:text-brand-light">
                Dashboard
              </Link>
              <Link href="/watchlist" className="hover:text-brand-light">
                Watchlist
              </Link>
              <Link href="/portfolio" className="hover:text-brand-light">
                Portfolio
              </Link>
              <Link href="/alerts" className="hover:text-brand-light">
                Alerts
              </Link>
              <Link href="/analytics" className="hover:text-brand-light">
                Analytics
              </Link>
              <Link href="/research" className="hover:text-brand-light">
                Research
              </Link>
            </div>
          </aside>
          <main className="app-content">{children}</main>
        </div>
      </body>
    </html>
  );
}