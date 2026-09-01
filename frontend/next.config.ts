import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Playwright uses a separate build directory, so browser tests never disrupt
  // a developer's already-running local Next server.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
};

export default nextConfig;
