import { Card, CardContent } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";

/**
 * App Router route-level loading state, shown while a route segment
 * compiles/loads. Pure skeleton (no spinners/text) so nav clicks feel
 * instant rather than frozen, matching the glass-card visual language.
 */
export default function Loading() {
  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-col gap-2">
          <Skeleton className="h-7 w-56" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="h-8 w-32 rounded-full" />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="flex flex-col gap-3 pt-5">
              <Skeleton className="h-3.5 w-24" />
              <Skeleton className="h-7 w-32" />
              <Skeleton className="h-3 w-40" />
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="flex flex-col gap-4 pt-5">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-40 w-full rounded-xl" />
        </CardContent>
      </Card>
    </div>
  );
}
