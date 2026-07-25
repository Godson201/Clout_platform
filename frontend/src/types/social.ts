export type SocialAccountStatus = "active" | "expired" | "revoked" | "disconnected";
export type PublishMode = "auto" | "manual";
export type SocialPostStatus = "pending" | "published" | "failed" | "deleted";

export interface SocialAccount {
  id: string;
  platform: string;
  external_account_id: string;
  handle: string;
  scopes: string[];
  status: SocialAccountStatus;
  token_expires_at: string | null;
  created_at: string;
}

export interface SocialPost {
  id: string;
  campaign_slot_id: string;
  social_account_id: string | null;
  platform: string;
  publish_mode: PublishMode;
  caption: string;
  external_post_id: string | null;
  post_url: string | null;
  status: SocialPostStatus;
  published_at: string | null;
  created_at: string;
}

export interface PostMetricSnapshot {
  id: string;
  views: number;
  likes: number;
  comments: number;
  shares: number | null;
  fetched_at: string;
}

export type CommentCategory = "question" | "suggestion" | "complaint" | "positive" | "negative" | "neutral" | "other";
export type SentimentLabel = "positive" | "negative" | "neutral";

export interface CommentAnalysis {
  category: CommentCategory;
  sentiment_label: SentimentLabel;
  sentiment_score: number;
  classifier_version: string;
}

export interface Comment {
  id: string;
  author_handle: string;
  text: string;
  posted_at: string | null;
  fetched_at: string;
  analysis: CommentAnalysis | null;
}
