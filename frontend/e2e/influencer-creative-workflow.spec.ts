import { expect, test, type Page, type Route } from "@playwright/test";

const slotId = "slot-e2e-1";
const nativePostId = "native-post-e2e-1";
let isPublished = false;
let selectedDeliveryIds: string[] = [];

const influencer = {
  id: "influencer-e2e-1",
  email: "creator@example.test",
  phone_number: null,
  user_type: "influencer",
  is_active: true,
  is_verified: true,
  created_at: "2026-01-01T00:00:00Z",
  roles: [],
};

const slot = {
  id: slotId,
  campaign_id: "campaign-e2e-1",
  platform: "instagram",
  tier: "micro",
  target_views: 2500,
  budget_allocated: "100.00",
  status: "claimed",
  influencer_id: influencer.id,
  claimed_at: "2026-01-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  delivered_pct: null,
  recovered_from_slot_id: null,
  recovery_generation: 0,
  brand_id: "brand-e2e-1",
  brand_name: "Clout Test Brand",
  advertisement_title: "Summer launch",
};

function creative() {
  return {
    id: "creative-e2e-1",
    campaign_slot_id: slotId,
    influencer_id: influencer.id,
    original_filename: "summer-launch.mp4",
    mime_type: "video/mp4",
    duration_seconds: 18.4,
    native_post_id: isPublished ? nativePostId : null,
    url: "https://example.test/summer-launch.mp4",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    headers: {
      "access-control-allow-origin": "http://localhost:3100",
      "access-control-allow-credentials": "true",
      "access-control-allow-headers": "authorization, content-type",
      "access-control-allow-methods": "GET, POST, OPTIONS",
    },
    body: JSON.stringify(body),
  });
}

async function mockWorkflowApi(page: Page) {
  // Match the API path rather than a host: developers may override
  // NEXT_PUBLIC_API_URL locally, but the browser contract is unchanged.
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();

    if (method === "OPTIONS") return json(route, {});

    if (path === "/api/v1/auth/refresh" && method === "POST") {
      return json(route, { access_token: "e2e-token", token_type: "bearer", user: influencer });
    }
    if (path === "/api/v1/slots/mine" && method === "GET") return json(route, [slot]);
    if (path === `/api/v1/slots/${slotId}/creative` && method === "GET") return json(route, creative());
    if (path === `/api/v1/slots/${slotId}/creative/publish` && method === "POST") {
      isPublished = true;
      return json(route, { native_post_id: nativePostId, caption: "Summer launch is here", feed_path: "/social" });
    }
    if (path === "/api/v1/social-accounts/me" && method === "GET") {
      return json(route, [
        { id: "account-instagram", platform: "instagram", handle: "creator", status: "active" },
        { id: "account-tiktok", platform: "tiktok", handle: "creatorclips", status: "active" },
      ]);
    }
    if (path === `/api/v1/social/posts/${nativePostId}/cross-posts` && method === "GET") return json(route, []);
    if (path === `/api/v1/social/posts/${nativePostId}/cross-post` && method === "POST") {
      selectedDeliveryIds = JSON.parse(request.postData() ?? "{}").social_account_ids ?? [];
      return json(route, selectedDeliveryIds.map((id: string) => ({
        id: `delivery-${id}`,
        social_account_id: id,
        platform: id.replace("account-", ""),
        status: "pending",
        post_url: null,
        error_message: null,
      })));
    }
    if (path === `/api/v1/slots/${slotId}/post`) return json(route, { detail: "Not found" }, 404);
    return json(route, []);
  });
}

test.beforeEach(async ({ page }) => {
  isPublished = false;
  selectedDeliveryIds = [];
  await mockWorkflowApi(page);
});

test("an influencer can publish a saved campaign creative to the public Clout feed", async ({ page }) => {
  await page.goto(`/influencer/slots/${slotId}`);

  await expect(page.getByText(/Saved draft/)).toBeVisible();
  await page.getByPlaceholder("Tell the Clout community about this campaign...").fill("Summer launch is here");
  const publishRequest = page.waitForRequest((request) =>
    request.method() === "POST" && request.url().endsWith(`/slots/${slotId}/creative/publish`),
  );
  await page.getByRole("button", { name: "Publish to public Clout feed" }).click();
  await expect((await publishRequest).postDataJSON()).toEqual({ caption: "Summer launch is here" });
});

test("an influencer chooses owned accounts before external delivery", async ({ page }) => {
  isPublished = true;
  await page.goto(`/influencer/slots/${slotId}`);

  await expect(page.getByText("Published to the public Clout feed")).toBeVisible();
  const instagramAccount = page.getByRole("checkbox", { name: "instagram @creator" });
  await instagramAccount.click();
  await expect(instagramAccount).toBeChecked();
  await expect(page.getByRole("button", { name: "Deliver to selected accounts" })).toBeEnabled();
  const deliveryRequest = page.waitForRequest((request) =>
    request.method() === "POST" && request.url().endsWith(`/social/posts/${nativePostId}/cross-post`),
  );
  await page.getByRole("button", { name: "Deliver to selected accounts" }).click();

  await expect((await deliveryRequest).postDataJSON()).toEqual({ social_account_ids: ["account-instagram"] });
});
