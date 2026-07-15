import { cn } from "@/lib/utils";

/**
 * Animated brand mark: a slowly rotating conic-gradient ring around a dark
 * tile containing a mini "price spark" polyline. Pure CSS animation (see
 * .brand-mark-ring in globals.css) so this stays a Server Component and can
 * be dropped into both the sidebar brand block and the mobile header link.
 *
 * Pass a unique `id` when rendering more than one instance on the same page
 * so the SVG gradient ids don't collide.
 */
export function BrandMark({ className, id = "brand-mark" }: { className?: string; id?: string }) {
  const gradientId = `${id}-spark`;

  return (
    <span
      className={cn(
        "relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl p-px shadow-glow transition-shadow duration-300 group-hover:shadow-[0_0_0_1px_rgb(94_234_212_/_0.55),0_0_28px_-4px_rgb(20_184_166_/_0.6)]",
        className
      )}
    >
      <span aria-hidden="true" className="brand-mark-ring absolute inset-0 rounded-xl" />
      <span className="relative flex h-full w-full items-center justify-center rounded-[11px] bg-[#0a0c10]">
        <svg
          viewBox="0 0 24 24"
          className="h-4 w-4"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id={gradientId} x1="2" y1="18" x2="21" y2="4" gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="#14B8A6" />
              <stop offset="1" stopColor="#8B5CF6" />
            </linearGradient>
          </defs>
          <polyline
            points="2,17 8,12.5 13,14.5 21,4"
            stroke={`url(#${gradientId})`}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ filter: "drop-shadow(0 0 4px rgb(20 184 166 / 0.8))" }}
          />
          <circle cx="21" cy="4" r="1.4" fill="#5EEAD4" />
        </svg>
      </span>
    </span>
  );
}
