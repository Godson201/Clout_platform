export interface AdvertisementTemplate {
  id: string;
  code: string;
  name: string;
  category: string;
  description: string | null;
  default_duration_seconds: number;
  is_active: boolean;
  created_at: string;
}

export type AdvertisementStatus = "draft" | "ready" | "archived";
export type AssetType = "video" | "image" | "logo" | "audio" | "voiceover";
export type AssetStatus = "uploaded" | "processing" | "ready" | "failed";
export type RenditionStatus = "pending" | "processing" | "ready" | "failed";
export type SocialPlatform = "tiktok" | "instagram" | "facebook" | "youtube";

export interface AdvertisementRendition {
  id: string;
  platform: SocialPlatform;
  status: RenditionStatus;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  error_message: string | null;
  url: string | null;
}

export interface AdvertisementAsset {
  id: string;
  asset_type: AssetType;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  status: AssetStatus;
  error_message: string | null;
  created_at: string;
  url: string | null;
  renditions: AdvertisementRendition[];
}

export interface Advertisement {
  id: string;
  brand_id: string;
  template_id: string;
  title: string;
  status: AdvertisementStatus;
  script_text: string | null;
  cta_text: string | null;
  hashtags: string[];
  duration_seconds: number | null;
  created_at: string;
  updated_at: string;
}

export interface AdvertisementDetail extends Advertisement {
  assets: AdvertisementAsset[];
}
