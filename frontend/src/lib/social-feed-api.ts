import { api } from "@/lib/api";

export interface SocialPost { id: string; body: string; created_at: string; author: { id: string; name: string; username?: string | null; picture_url?: string | null }; like_count: number; comment_count: number; liked_by_me: boolean; saved_by_me: boolean; media: { id: string; media_type: string; mime_type: string; url: string }[] }
export interface SocialComment { id: string; body: string; created_at: string; author: SocialPost["author"] }

export async function listFeed() { const { data } = await api.get<SocialPost[]>("/social/feed"); return data; }
export async function createPost(body: string) { const { data } = await api.post<SocialPost>("/social/posts", { body }); return data; }
export async function togglePostLike(id: string) { const { data } = await api.post<SocialPost>(`/social/posts/${id}/like`); return data; }
export async function togglePostSave(id: string) { const { data } = await api.post<SocialPost>(`/social/posts/${id}/save`); return data; }
export async function listPostComments(id: string) { const { data } = await api.get<SocialComment[]>(`/social/posts/${id}/comments`); return data; }
export async function addPostComment(id: string, body: string) { const { data } = await api.post<SocialComment>(`/social/posts/${id}/comments`, { body }); return data; }
export async function uploadPostMedia(id: string, file: File) { const form = new FormData(); form.append("file", file); await api.post(`/social/posts/${id}/media`, form); }
