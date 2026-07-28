export interface DailyViews {
  day: string;
  views: number;
}

export interface TopCampaign {
  campaign_id: string;
  title: string;
  platforms: string[];
  influencer_avatars: (string | null)[];
  total_views: number;
  progress_pct: number;
  status: string;
}

export interface BrandDashboardSummary {
  total_campaigns: number;
  total_campaigns_mom_pct: number | null;
  total_views: number;
  total_views_mom_pct: number | null;
  total_engagement: number;
  total_engagement_mom_pct: number | null;
  total_spent: number;
  total_spent_mom_pct: number | null;
  currency: string;
  views_over_time: DailyViews[];
  views_by_platform: Record<string, number>;
  top_campaigns: TopCampaign[];
}
