export type HighlightCategory = "award" | "event";

export interface ProfileHighlight {
  id: string;
  category: HighlightCategory;
  title: string;
  subtitle: string | null;
  occurred_on: string | null;
  description: string | null;
  created_at: string;
}

export interface PublicProfileCommon {
  legacy: string | null;
  location: string | null;
  province: string | null;
  awards: ProfileHighlight[];
  events: ProfileHighlight[];
}

export interface PublicBrandProfile extends PublicProfileCommon {
  id: string;
  business_name: string;
  sector: string | null;
  logo_url: string | null;
  verification_status: string;
  description: string | null;
  website: string | null;
  contact_email: string | null;
  contact_phone: string | null;
}

export interface PublicInfluencerProfile extends PublicProfileCommon {
  id: string;
  display_name: string;
  username: string;
  sector: string | null;
  profile_picture_url: string | null;
  verification_status: string;
  bio: string | null;
  follower_tier: string | null;
  estimated_followers: number | null;
}
