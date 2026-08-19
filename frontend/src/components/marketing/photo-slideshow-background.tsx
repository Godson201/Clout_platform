"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

const DEFAULT_IMAGES = Array.from(
  { length: 16 },
  (_, i) => `/images/slide-${String(i + 1).padStart(2, "0")}.jpg`,
);

/** Full-bleed, auto-crossfading photo background — real creators/brands using
 * their phones, sourced from public/images. Always meant to be paired with
 * <PremiumGradientBackground photoBehind /> stacked directly on top: that's
 * what supplies the color-graded tint/scrim that keeps hero/login copy
 * legible, so this component renders the photos at full brightness with no
 * tint of its own (stacking two independent dark overlays would bury the
 * photo entirely). Pure CSS crossfade (opacity), no JS animation library.
 * Pauses for prefers-reduced-motion.
 */
export function PhotoSlideshowBackground({
  images = DEFAULT_IMAGES,
  intervalMs = 4500,
  className = "",
}: {
  images?: string[];
  intervalMs?: number;
  className?: string;
}) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (images.length < 2) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const id = setInterval(() => setIndex((i) => (i + 1) % images.length), intervalMs);
    return () => clearInterval(id);
  }, [images.length, intervalMs]);

  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden="true">
      {images.map((src, i) => (
        <Image
          key={src}
          src={src}
          alt=""
          fill
          priority={i === 0}
          quality={90}
          sizes="100vw"
          className="object-cover duration-1800 transition-opacity ease-in-out"
          style={{ opacity: i === index ? 1 : 0 }}
        />
      ))}
    </div>
  );
}
