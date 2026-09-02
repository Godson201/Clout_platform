import { api } from "@/lib/api";

export type PostVisibility = "public" | "followers" | "brands_only" | "private";
export interface SocialPost { id: string; body: string; created_at: string; author: { id: string; name: string; username?: string | null; picture_url?: string | null }; like_count: number; comment_count: number; liked_by_me: boolean; saved_by_me: boolean; visibility: PostVisibility; hashtags?: string[]; media: { id: string; media_type: string; mime_type: string; url: string; processing_status: "pending" | "processing" | "ready" | "failed" }[] }
export interface SocialComment { id: string; body: string; created_at: string; author: SocialPost["author"] }

export async function listFeed() { const { data } = await api.get<SocialPost[]>("/social/feed"); return data; }
export async function listForYouFeed() { const { data } = await api.get<SocialPost[]>("/social/for-you"); return data; }
export async function listTrendingPosts() { const { data } = await api.get<SocialPost[]>("/social/trending"); return data; }
export async function listHashtagPosts(name: string) { const { data } = await api.get<SocialPost[]>(`/social/hashtags/${encodeURIComponent(name)}`); return data; }
export async function createPost(body: string, visibility: PostVisibility) { const { data } = await api.post<SocialPost>("/social/posts", { body, visibility }); return data; }
export async function togglePostLike(id: string) { const { data } = await api.post<SocialPost>(`/social/posts/${id}/like`); return data; }
export async function togglePostSave(id: string) { const { data } = await api.post<SocialPost>(`/social/posts/${id}/save`); return data; }
export async function listPostComments(id: string) { const { data } = await api.get<SocialComment[]>(`/social/posts/${id}/comments`); return data; }
export async function addPostComment(id: string, body: string) { const { data } = await api.post<SocialComment>(`/social/posts/${id}/comments`, { body }); return data; }
export async function uploadPostMedia(id: string, file: File) { const form = new FormData(); form.append("file", file); await api.post(`/social/posts/${id}/media`, form); }
export async function crossPost(id: string, socialAccountIds: string[]) { const { data } = await api.post(`/social/posts/${id}/cross-post`, { social_account_ids: socialAccountIds }); return data; }
export interface CrossPostDelivery { id: string; social_account_id: string; platform: string; status: "pending" | "published" | "failed" | "deleted"; post_url: string | null; error_message: string | null; }
export async function listCrossPosts(id: string) { const { data } = await api.get<CrossPostDelivery[]>(`/social/posts/${id}/cross-posts`); return data; }
export async function retryCrossPost(postId: string, distributionId: string) { const { data } = await api.post<CrossPostDelivery>(`/social/posts/${postId}/cross-posts/${distributionId}/retry`); return data; }
export async function reportPost(id: string, reason: string) { await api.post(`/social/posts/${id}/report`, { reason }); }
export async function blockUser(id: string) { await api.post(`/social/users/${id}/block`); }
export async function searchProfiles(q: string, filters: Record<string, string> = {}) { const { data } = await api.get<SocialPost["author"][]>("/social/search", { params: { q, ...filters } }); return data; }
export async function listCreators() { const { data } = await api.get<SocialPost["author"][]>("/social/creators"); return data; }
export async function getSocialProfile(id: string) { const { data } = await api.get<{ author: SocialPost["author"]; follower_count: number; following_count: number; following_by_me: boolean; posts: SocialPost[] }>(`/social/profiles/${id}`); return data; }
export async function toggleFollow(id: string) { const { data } = await api.post<{ following: boolean; follower_count: number; following_count: number }>(`/social/users/${id}/follow`); return data; }
export async function listProfileFollowers(id: string) { const { data } = await api.get<{ items: SocialPost["author"][]; total: number }>(`/social/profiles/${id}/followers`); return data; }
export async function listProfileFollowing(id: string) { const { data } = await api.get<{ items: SocialPost["author"][]; total: number }>(`/social/profiles/${id}/following`); return data; }
export async function repostPost(id: string) { const { data } = await api.post<SocialPost>(`/social/posts/${id}/repost`); return data; }
