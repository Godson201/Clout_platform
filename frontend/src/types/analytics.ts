export interface InfluencerPerformance {
  influencer_id: string;
  username: string;
  platform: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
}

export interface CommentSentimentSummary {
  total_comments: number;
  category_counts: Record<string, number>;
  average_sentiment_score: number | null;
  sample_questions: string[];
}

export interface CampaignAnalytics {
  total_target_views: number;
  total_verified_views: number;
  progress_pct: number;
  total_engagement: number;
  views_by_platform: Record<string, number>;
  engagement_by_platform: Record<string, number>;
  influencer_performance: InfluencerPerformance[];
  top_influencer_username: string | null;
  top_platform: string | null;
  slot_status_counts: Record<string, number>;
  comment_summary: CommentSentimentSummary;
}

export interface AwaitingSettlementItem {
  slot_id: string;
  campaign_id: string;
  platform: string;
  tier: string;
  status: string;
  target_views: number;
  budget_allocated: string;
  brand_name: string;
  influencer_username: string;
  post_url: string | null;
  published_at: string | null;
  window_closed_at: string;
}
