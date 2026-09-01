import { api } from "@/lib/api";

export interface SocialReportQueueItem {
  report_id: string;
  post_id: string;
  author_id: string;
  body: string;
  reason: string;
  details: string | null;
  created_at: string;
}

export interface ArchivedSocialPost {
  post_id: string;
  author_id: string;
  body: string;
  updated_at: string;
}

export async function listSocialReports(): Promise<SocialReportQueueItem[]> {
  const { data } = await api.get<SocialReportQueueItem[]>("/admin/social-moderation/reports");
  return data;
}

export async function resolveSocialReport(reportId: string, archivePost: boolean, note?: string): Promise<void> {
  await api.post(`/admin/social-moderation/reports/${reportId}/resolve`, { archive_post: archivePost, note: note || null });
}

export async function listArchivedSocialPosts(): Promise<ArchivedSocialPost[]> {
  const { data } = await api.get<ArchivedSocialPost[]>("/admin/social-moderation/posts/archived");
  return data;
}

export async function restoreSocialPost(postId: string): Promise<void> {
  await api.post(`/admin/social-moderation/posts/${postId}/restore`);
}
