import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const { searchProfiles, listTrendingPosts, listHashtagPosts } = vi.hoisted(() => ({
  searchProfiles: vi.fn(),
  listTrendingPosts: vi.fn(),
  listHashtagPosts: vi.fn(),
}));
vi.mock("@/lib/social-feed-api", () => ({ searchProfiles, listTrendingPosts, listHashtagPosts }));
vi.mock("@/components/auth/require-user-type", () => ({ RequireUserType: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock("@/components/dashboard/dashboard-shell", () => ({ DashboardShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));

import DiscoverPage from "./page";

function renderPage() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><DiscoverPage /></QueryClientProvider>);
}

describe("Discovery", () => {
  it("searches profiles with selected filters", async () => {
    searchProfiles.mockResolvedValue([{ id: "creator-1", name: "Clout Creator", username: "cloutcreator" }]);
    listTrendingPosts.mockResolvedValue([]);
    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByPlaceholderText("Search name or @username"), "cl");
    fireEvent.change(screen.getByPlaceholderText("Sector or niche"), { target: { value: "beauty" } });
    await waitFor(() => expect(searchProfiles).toHaveBeenLastCalledWith("cl", expect.objectContaining({ sector: "beauty" })));
    expect(await screen.findByText("Clout Creator")).toBeInTheDocument();
  });

  it("opens matching posts from a trending hashtag", async () => {
    searchProfiles.mockResolvedValue([]);
    listTrendingPosts.mockResolvedValue([{ id: "post-1", body: "New #beauty launch", author: { id: "creator-1", name: "Creator" }, like_count: 2, comment_count: 1, media: [], hashtags: ["beauty"] }]);
    listHashtagPosts.mockResolvedValue([{ id: "post-2", body: "Beauty post", author: { id: "creator-2", name: "Beauty Creator" }, like_count: 0, comment_count: 0, media: [] }]);
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "#beauty" }));
    await waitFor(() => expect(listHashtagPosts).toHaveBeenCalledWith("beauty"));
    expect(await screen.findByText("Beauty post")).toBeInTheDocument();
  });
});
