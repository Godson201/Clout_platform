export type NotificationType = "new_brand_media" | "influencer_post_published" | "slot_claimed" | "payment_confirmed";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  link: string | null;
  data: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}
