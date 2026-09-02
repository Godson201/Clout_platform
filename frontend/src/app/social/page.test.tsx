import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const { listForYouFeed, listFeed, reportPost, blockUser, createPost, uploadPostMedia, togglePostLike, togglePostSave, listPostComments, addPostComment, repostPost } = vi.hoisted(() => ({
  listForYouFeed: vi.fn(),
  listFeed: vi.fn(),
  reportPost: vi.fn(),
  blockUser: vi.fn(),
  createPost: vi.fn(),
  uploadPostMedia: vi.fn(),
  togglePostLike: vi.fn(),
  togglePostSave: vi.fn(),
  listPostComments: vi.fn().mockResolvedValue([]),
  addPostComment: vi.fn(),
  repostPost: vi.fn(),
}));
vi.mock("@/lib/social-feed-api", () => ({
  listForYouFeed,
  listFeed,
  reportPost,
  blockUser,
  createPost,
  uploadPostMedia,
  togglePostLike,
  togglePostSave,
  listPostComments,
  addPostComment,
  repostPost,
}));
vi.mock("@/components/auth/require-user-type", () => ({ RequireUserType: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock("@/components/dashboard/dashboard-shell", () => ({ DashboardShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock("@/store/auth-store", () => ({ useAuthStore: (selector: (state: { user: { id: string } }) => unknown) => selector({ user: { id: "viewer" } }) }));

import SocialPage from "./page";

describe("Clout feed safety controls", () => {
  it("reports a post with the selected reason", async () => {
    listForYouFeed.mockResolvedValue([{ id: "post-1", body: "Suspicious message", author: { id: "creator-1", name: "Creator" }, like_count: 0, comment_count: 0, liked_by_me: false, saved_by_me: false, visibility: "public", media: [] }]);
    listFeed.mockResolvedValue([]);
    reportPost.mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><SocialPage /></QueryClientProvider>);
    await user.click(await screen.findByRole("button", { name: "Report" }));
    await user.selectOptions(screen.getAllByRole("combobox").at(-1)!, "harassment");
    await user.click(screen.getByRole("button", { name: "Submit report" }));
    await waitFor(() => expect(reportPost).toHaveBeenCalledWith("post-1", "harassment"));
  });

  it("blocks a creator and refreshes the social feed", async () => {
    listForYouFeed.mockResolvedValue([{ id: "post-2", body: "Block this creator", author: { id: "creator-2", name: "Creator Two" }, like_count: 0, comment_count: 0, liked_by_me: false, saved_by_me: false, visibility: "public", media: [] }]);
    blockUser.mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><SocialPage /></QueryClientProvider>);
    await user.click(await screen.findByRole("button", { name: "Block creator" }));
    await waitFor(() => expect(blockUser).toHaveBeenCalledWith("creator-2"));
  });
});
