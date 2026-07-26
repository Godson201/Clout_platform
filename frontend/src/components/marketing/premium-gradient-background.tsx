/** Full-bleed premium background: navy → ocean → teal gradient, layered mesh
 * glows, translucent geometric shapes, and a flowing wave silhouette at the
 * base. Absolutely positioned (`inset-0`) — the parent must be `relative`
 * (or the nearest positioned ancestor) and taller than the content it frames.
 * Pure CSS/SVG, no images, so it stays crisp and fast at any viewport size.
 */
export function PremiumGradientBackground({ className = "" }: { className?: string }) {
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden="true">
      {/* Base gradient */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(160deg, #071A2F 0%, #0C5E82 55%, #00A8C6 100%)",
        }}
      />

      {/* Soft mesh glows */}
      <div
        className="absolute -top-24 -left-24 size-[32rem] rounded-full opacity-40 blur-3xl animate-float"
        style={{ background: "radial-gradient(circle, rgba(0,168,198,0.55) 0%, transparent 70%)" }}
      />
      <div
        className="absolute top-1/3 -right-32 size-[36rem] rounded-full opacity-30 blur-3xl animate-float"
        style={{ background: "radial-gradient(circle, rgba(37,99,235,0.5) 0%, transparent 70%)", animationDelay: "1.5s" }}
      />
      <div
        className="absolute bottom-0 left-1/4 size-[28rem] rounded-full opacity-25 blur-3xl animate-float"
        style={{ background: "radial-gradient(circle, rgba(255,255,255,0.35) 0%, transparent 70%)", animationDelay: "3s" }}
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
