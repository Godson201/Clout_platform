export type ContractStatus = "proposed" | "accepted" | "declined" | "cancelled";

export interface Contract {
  id: string;
  brand_id: string;
  influencer_id: string;
  campaign_id: string | null;
  title: string;
  terms_text: string;
  status: ContractStatus;
  proposed_by_user_id: string;
  responded_by_user_id: string | null;
  responded_at: string | null;
  created_at: string;
}

export interface AdminContract extends Contract {
  brand_name: string;
  influencer_username: string;
}
