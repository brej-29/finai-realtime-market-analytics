import Link from "next/link";

import { SearchX } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-surface text-muted">
        <SearchX className="h-6 w-6" />
      </div>
      <h1 className="mt-5 font-display text-lg font-semibold text-foreground">Page not found</h1>
      <p className="mt-2 max-w-sm text-sm text-muted">
        This page doesn&apos;t exist. It may have been moved or the address mistyped.
      </p>
      <Link
        href="/"
        className="mt-6 inline-flex h-10 items-center justify-center gap-2 whitespace-nowrap rounded-xl bg-brand px-4 text-sm font-medium text-slate-950 shadow-soft transition-colors hover:bg-brand-light"
      >
        Go to dashboard
      </Link>
    </div>
  );
}
