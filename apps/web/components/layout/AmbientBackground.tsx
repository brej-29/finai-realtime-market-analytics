/**
 * Layered ambient backdrop for the app shell: three slow-drifting aurora
 * blobs, a masked dot-grid, and a faint film-grain noise layer. Pure CSS
 * animation (see globals.css) so this can stay a Server Component.
 */
export function AmbientBackground() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="ambient-blob ambient-blob-teal" />
      <div className="ambient-blob ambient-blob-indigo" />
      <div className="ambient-blob ambient-blob-violet" />
      <div className="ambient-dot-grid" />
      <div className="ambient-grain" />
    </div>
  );
}
