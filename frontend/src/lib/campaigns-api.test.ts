import { describe, expect, it, vi } from "vitest";

const { post } = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: { post } }));

import { publishSlotCreative, uploadSlotCreative } from "@/lib/campaigns-api";

describe("campaign creative API", () => {
  it("uploads the finished video as multipart form data", async () => {
    post.mockResolvedValueOnce({ data: { id: "creative-1" } });
    const file = new File(["video"], "finished.mp4", { type: "video/mp4" });
    await uploadSlotCreative("slot-1", file);
    expect(post).toHaveBeenCalledWith("/slots/slot-1/creative", expect.any(FormData));
    expect((post.mock.calls[0][1] as FormData).get("file")).toBe(file);
  });

  it("publishes a saved creative with its public caption", async () => {
    post.mockResolvedValueOnce({ data: { native_post_id: "post-1", caption: "Campaign launch", feed_path: "/social" } });
    await expect(publishSlotCreative("slot-1", "Campaign launch")).resolves.toMatchObject({ native_post_id: "post-1" });
    expect(post).toHaveBeenCalledWith("/slots/slot-1/creative/publish", { caption: "Campaign launch" });
  });
});
