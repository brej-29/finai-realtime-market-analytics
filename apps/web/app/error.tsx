"use client";

import { useEffect } from "react";

import Link from "next/link";

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/Button";

export default function Error(props: { error: Error & { digest?: string }; reset: () => void }) {
  const { error, reset } = props;

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-negative/10 text-negative">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <h1 className="mt-5 font-display text-lg font-semibold text-foreground">Something went wrong</h1>
      <p className="mt-2 max-w-sm text-sm text-muted">
        The dashboard hit an unexpected error. Your data is safe — try again.
      </p>
      <div className="mt-6 flex items-center gap-3">
        <Button variant="primary" onClick={() => reset()}>
          Try again
        </Button>
        <Link
          href="/"
          className="inline-flex h-10 items-center justify-center gap-2 whitespace-nowrap rounded-xl px-4 text-sm font-medium text-muted transition-colors hover:bg-surface-hover hover:text-foreground"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
