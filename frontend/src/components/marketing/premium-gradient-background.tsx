/** Full-bleed premium background: navy → ocean → teal gradient, layered mesh
 * glows, translucent geometric shapes, and a flowing wave silhouette at the
 * base. Absolutely positioned (`inset-0`) — the parent must be `relative`
 * (or the nearest positioned ancestor) and taller than the content it frames.
 * Pure CSS/SVG, no images, so it stays crisp and fast at any viewport size.
 *
 * `photoBehind` thins the base gradient into a color-graded tint (like a
 * duotone photo treatment) instead of an opaque fill, for stacking on top of
 * PhotoSlideshowBackground — everything else (glows/shapes/waves) is already
 * translucent and works unchanged over a photo.
 */
export function PremiumGradientBackground({
  className = "",
  photoBehind = false,
}: {
  className?: string;
  photoBehind?: boolean;
}) {
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden="true">
      {/* Base gradient */}
      <div
        className="absolute inset-0"
        style={{
          background: "linear-gradient(160deg, #071827 0%, #0C4A6E 55%, #0EA5E9 100%)",
          opacity: photoBehind ? 0.72 : 1,
        }}
      />

      {/* Soft mesh glows */}
      <div
        className="absolute -top-24 -left-24 size-[32rem] rounded-full opacity-40 blur-3xl animate-float"
        style={{ background: "radial-gradient(circle, rgba(14,165,233,0.55) 0%, transparent 70%)" }}
      />
      <div
        className="absolute top-1/3 -right-32 size-[36rem] rounded-full opacity-30 blur-3xl animate-float"
        style={{ background: "radial-gradient(circle, rgba(56,189,248,0.5) 0%, transparent 70%)", animationDelay: "1.5s" }}
      />
      <div
        className="absolute bottom-0 left-1/4 size-[28rem] rounded-full opacity-25 blur-3xl animate-float"
        style={{ background: "radial-gradient(circle, rgba(125,211,252,0.4) 0%, transparent 70%)", animationDelay: "3s" }}
      />

      {/* Translucent geometric shapes */}
      <div className="absolute top-16 right-[12%] size-40 rotate-12 rounded-[28px] border border-white/15 bg-white/5 backdrop-blur-sm" />
      <div className="absolute bottom-24 left-[8%] size-28 -rotate-6 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm" />
      <div className="absolute top-1/2 left-[45%] size-16 rotate-45 rounded-xl border border-white/10 bg-white/5" />

      {/* Flowing wave silhouette along the bottom edge */}
      <svg
        className="absolute inset-x-0 bottom-0 h-40 w-full text-white/[0.06]"
        viewBox="0 0 1440 220"
        preserveAspectRatio="none"
        fill="currentColor"
      >
        <path d="M0,120 C240,200 480,40 720,90 C960,140 1200,60 1440,110 L1440,220 L0,220 Z" />
      </svg>
      <svg
        className="absolute inset-x-0 bottom-0 h-28 w-full text-white/[0.05]"
        viewBox="0 0 1440 180"
        preserveAspectRatio="none"
        fill="currentColor"
      >
        <path d="M0,80 C320,150 640,10 960,70 C1180,110 1320,60 1440,80 L1440,180 L0,180 Z" />
      </svg>
    </div>
  );
}
