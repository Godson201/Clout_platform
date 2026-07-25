export type UserType = "brand" | "influencer" | "admin";

export interface User {
  id: string;
  email: string;
  phone_number: string | null;
  user_type: UserType;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  roles: string[];
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type VerificationStatus = "unverified" | "pending" | "approved" | "rejected";

export interface Brand {
  id: string;
  business_name: string;
  sector: string | null;
  location: string | null;
  description: string | null;
  website: string | null;
  logo_url: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  verification_status: VerificationStatus;
  created_at: string;
}

export type FollowerTier = "nano" | "micro" | "mid" | "macro";

export interface Influencer {
  id: string;
  display_name: string;
  username: string;
  location: string | null;
  sector: string | null;
  bio: string | null;
  follower_tier: FollowerTier | null;
  estimated_followers: number | null;
  completed_slots_count: number;
  failed_slots_count: number;
  verification_status: VerificationStatus;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
