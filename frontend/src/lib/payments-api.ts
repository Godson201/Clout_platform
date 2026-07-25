import { api } from "@/lib/api";
import type { Page } from "@/types/auth";
import type { Payout, Wallet } from "@/types/payment";

export async function getMyBrandWallet(): Promise<Wallet> {
  const { data } = await api.get<Wallet>("/brands/me/wallet");
  return data;
}

export async function getMyInfluencerWallet(): Promise<Wallet> {
  const { data } = await api.get<Wallet>("/influencers/me/wallet");
  return data;
}

export async function requestPayout(amount: string, phoneNumber: string): Promise<Payout> {
  const { data } = await api.post<Payout>("/influencers/me/payouts", { amount, phone_number: phoneNumber });
  return data;
}

export async function listPayouts(page = 1, pageSize = 20): Promise<Page<Payout>> {
  const { data } = await api.get<Page<Payout>>("/influencers/me/payouts", { params: { page, page_size: pageSize } });
  return data;
}

export async function getPayout(id: string): Promise<Payout> {
  const { data } = await api.get<Payout>(`/influencers/me/payouts/${id}`);
  return data;
}
