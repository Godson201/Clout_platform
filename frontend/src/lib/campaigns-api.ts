import { api } from "@/lib/api";
import type { CampaignAnalytics } from "@/types/analytics";
import type { AssetModerationQueueItem } from "@/types/advertisement";
import type { Page } from "@/types/auth";
import type { Campaign, CampaignCreative, CampaignDetail, MarketplaceSlot, MySlot } from "@/types/campaign";
import type { CampaignFundingResponse, Payment } from "@/types/payment";
import type { CampaignReport } from "@/types/report";

export interface CreateCampaignInput {
  advertisement_id: string;
  platforms: string[];
  target_views: number;
  tier: string;
  slot_count: number;
  performance_window_days?: number;
  target_sector?: string;
  target_location?: string;
}

export async function createCampaign(input: CreateCampaignInput): Promise<Campaign> {
  const { data } = await api.post<Campaign>("/campaigns", input);
  return data;
}

export async function listCampaigns(page = 1, pageSize = 20): Promise<Page<Campaign>> {
  const { data } = await api.get<Page<Campaign>>("/campaigns", { params: { page, page_size: pageSize } });
  return data;
}

export async function getCampaign(id: string): Promise<CampaignDetail> {
  const { data } = await api.get<CampaignDetail>(`/campaigns/${id}`);
  return data;
}

export async function fundCampaign(id: string, phoneNumber: string): Promise<CampaignFundingResponse> {
  const { data } = await api.post<CampaignFundingResponse>(`/campaigns/${id}/fund`, { phone_number: phoneNumber });
  return data;
}

export async function getCampaignPayment(id: string): Promise<Payment> {
  const { data } = await api.get<Payment>(`/campaigns/${id}/payment`);
  return data;
}

export async function cancelCampaign(id: string, phoneNumber?: string): Promise<CampaignDetail> {
  const { data } = await api.post<CampaignDetail>(`/campaigns/${id}/cancel`, { phone_number: phoneNumber });
  return data;
}

export async function getCampaignAnalytics(id: string): Promise<CampaignAnalytics> {
  const { data } = await api.get<CampaignAnalytics>(`/campaigns/${id}/analytics`);
  return data;
}

export async function generateCampaignReport(id: string): Promise<CampaignReport> {
  const { data } = await api.post<CampaignReport>(`/campaigns/${id}/report`);
  return data;
}

export async function getLatestCampaignReport(id: string): Promise<CampaignReport> {
  const { data } = await api.get<CampaignReport>(`/campaigns/${id}/report`);
  return data;
}

export interface MarketplaceFilters {
  platform?: string;
  tier?: string;
  sector?: string;
  location?: string;
}

export async function browseMarketplace(filters: MarketplaceFilters = {}): Promise<MarketplaceSlot[]> {
  const { data } = await api.get<MarketplaceSlot[]>("/marketplace/slots", { params: filters });
  return data;
}

export async function claimSlot(slotId: string) {
  const { data } = await api.post(`/slots/${slotId}/claim`);
  return data;
}

export async function browseApprovedMedia(): Promise<AssetModerationQueueItem[]> {
  const { data } = await api.get<AssetModerationQueueItem[]>("/marketplace/media");
  return data;
}

export async function listMySlots(): Promise<MySlot[]> {
  const { data } = await api.get<MySlot[]>("/slots/mine");
  return data;
}

export async function getSlotCreative(slotId: string): Promise<CampaignCreative> {
  const { data } = await api.get<CampaignCreative>(`/slots/${slotId}/creative`);
  return data;
}

export async function uploadSlotCreative(slotId: string, file: File): Promise<CampaignCreative> {
  const body = new FormData();
  body.append("file", file);
  const { data } = await api.post<CampaignCreative>(`/slots/${slotId}/creative`, body);
  return data;
}

export async function publishSlotCreative(slotId: string, caption: string): Promise<{ native_post_id: string; caption: string; feed_path: string }> {
  const { data } = await api.post<{ native_post_id: string; caption: string; feed_path: string }>(`/slots/${slotId}/creative/publish`, { caption });
  return data;
}
