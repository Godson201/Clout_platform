export type PaymentStatus = "pending" | "successful" | "failed";
export type PaymentProvider = "momo" | "mock";

export interface Payment {
  id: string;
  campaign_id: string;
  provider: PaymentProvider;
  provider_reference: string;
  phone_number: string;
  amount: string;
  currency: string;
  status: PaymentStatus;
  failure_reason: string | null;
  confirmed_at: string | null;
  created_at: string;
}

export interface CampaignFundingResponse {
  campaign: import("@/types/campaign").Campaign;
  payment: Payment;
}

export interface Wallet {
  id: string;
  owner_type: "brand" | "influencer" | "platform" | "escrow" | "external";
  owner_id: string | null;
  currency: string;
  balance: string;
}

export interface Payout {
  id: string;
  influencer_id: string;
  provider: PaymentProvider;
  provider_reference: string;
  phone_number: string;
  amount: string;
  fee_pct: string;
  fee_amount: string;
  net_amount: string;
  currency: string;
  status: PaymentStatus;
  failure_reason: string | null;
  completed_at: string | null;
  created_at: string;
}
