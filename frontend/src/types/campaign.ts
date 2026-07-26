import type { SocialPlatform } from "@/types/advertisement";

export type CampaignStatus =
  | "draft"
  | "pending_funding"
  | "funded"
  | "listed"
  | "active"
  | "completed"
  | "cancelled";

export type SlotStatus =
  | "open"
  | "claimed"
  | "published"
  | "tracking"
  | "completed"
  | "partially_completed"
  | "failed"
  | "recovered"
  | "cancelled";

export type FollowerTier = "nano" | "micro" | "mid" | "macro";

export interface Campaign {
  id: string;
  brand_id: string;
  advertisement_id: string;
  status: CampaignStatus;
  platforms: string[];
  target_views: number;
  tier: FollowerTier;
  slot_count: number;
  performance_window_days: number;
  target_sector: string | null;
  target_location: string | null;
  rate_snapshot: Record<string, string>;
  brand_fee_pct: string;
  base_price: string;
  total_brand_payment: string;
  currency: string;
  created_at: string;
  updated_at: string;
}

export interface CampaignSlot {
  id: string;
  campaign_id: string;
  platform: SocialPlatform;
  tier: FollowerTier;
  target_views: number;
  budget_allocated: string;
  status: SlotStatus;
  influencer_id: string | null;
  claimed_at: string | null;
  created_at: string;
  delivered_pct: string | null;
  recovered_from_slot_id: string | null;
  recovery_generation: number;
}

export interface CampaignDetail extends Campaign {
  slots: CampaignSlot[];
  escrow_balance: string | null;
}

export interface MatchScoreBreakdown {
  sector_score: number;
  location_score: number;
  tier_score: number;
  reliability_score: number;
  platform_score: number;
  engagement_score: number;
  total: number;
}

export interface MarketplaceSlot extends CampaignSlot {
  brand_name: string;
  advertisement_title: string;
  campaign_target_sector: string | null;
  campaign_target_location: string | null;
  match_score: MatchScoreBreakdown;
  historical_boost: number;
  final_score: number;
}

export interface MySlot extends CampaignSlot {
  brand_id: string;
  brand_name: string;
  advertisement_title: string;
}
