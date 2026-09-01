import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:3100";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command:
          process.platform === "win32"
            ? "set \"NEXT_DIST_DIR=.next-e2e\" && npx next dev -p 3100"
            : "NEXT_DIST_DIR=.next-e2e npx next dev -p 3100",
        url: baseURL,
        reuseExistingServer: false,
        timeout: 120_000,
      },
  // Use the full Chromium binary. It is also the binary available in lean CI
  // images, where the optional headless-shell download may be omitted.
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], channel: "chromium" } }],
});
