import { api } from "@/lib/api";
import type { Comment, PostMetricSnapshot, SocialAccount, SocialPost } from "@/types/social";

export async function getConnectUrl(platform: string): Promise<string> {
  const { data } = await api.get<{ authorization_url: string }>(`/social-accounts/connect/${platform}`);
  return data.authorization_url;
}

export async function completeOAuthCallback(platform: string, code: string, state: string): Promise<SocialAccount> {
  const { data } = await api.post<SocialAccount>(`/social-accounts/callback/${platform}`, { code, state });
  return data;
}

export async function listMySocialAccounts(): Promise<SocialAccount[]> {
  const { data } = await api.get<SocialAccount[]>("/social-accounts/me");
  return data;
}

export async function disconnectSocialAccount(id: string): Promise<void> {
  await api.delete(`/social-accounts/${id}`);
}

export async function createSlotPost(slotId: string, socialAccountId: string, caption: string): Promise<SocialPost> {
  const { data } = await api.post<SocialPost>(`/slots/${slotId}/post`, {
    social_account_id: socialAccountId,
    caption,
  });
  return data;
}

export async function getSlotPost(slotId: string): Promise<SocialPost> {
  const { data } = await api.get<SocialPost>(`/slots/${slotId}/post`);
  return data;
}

export async function submitSlotPostUrl(slotId: string, postUrl: string): Promise<SocialPost> {
  const { data } = await api.patch<SocialPost>(`/slots/${slotId}/post/submit-url`, { post_url: postUrl });
  return data;
}

export async function getSlotPostMetrics(slotId: string): Promise<PostMetricSnapshot[]> {
  const { data } = await api.get<PostMetricSnapshot[]>(`/slots/${slotId}/post/metrics`);
  return data;
}

export async function getSlotPostComments(slotId: string): Promise<Comment[]> {
  const { data } = await api.get<Comment[]>(`/slots/${slotId}/post/comments`);
  return data;
}
