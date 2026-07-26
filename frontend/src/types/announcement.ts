export type AnnouncementAudience = "all" | "brands" | "influencers";

export interface Announcement {
  id: string;
  title: string;
  body: string;
  audience: AnnouncementAudience;
  is_active: boolean;
  created_at: string;
}
