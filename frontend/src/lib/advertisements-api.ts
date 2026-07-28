import { api } from "@/lib/api";
import type {
  Advertisement,
  AdvertisementAsset,
  AdvertisementDetail,
  AdvertisementTemplate,
  AssetModerationQueueItem,
  AssetType,
} from "@/types/advertisement";
import type { Page } from "@/types/auth";

export async function listTemplates(): Promise<AdvertisementTemplate[]> {
  const { data } = await api.get<AdvertisementTemplate[]>("/templates");
  return data;
}

export interface CreateAdvertisementInput {
  template_id: string;
  title: string;
  script_text?: string;
  cta_text?: string;
  hashtags?: string[];
  duration_seconds?: number;
}

export async function createAdvertisement(input: CreateAdvertisementInput): Promise<Advertisement> {
  const { data } = await api.post<Advertisement>("/advertisements", input);
  return data;
}

export async function listAdvertisements(
  page = 1,
  pageSize = 20,
  status?: Advertisement["status"],
): Promise<Page<Advertisement>> {
  const { data } = await api.get<Page<Advertisement>>("/advertisements", {
    params: { page, page_size: pageSize, ...(status ? { status } : {}) },
  });
  return data;
}

export async function getAdvertisement(id: string): Promise<AdvertisementDetail> {
  const { data } = await api.get<AdvertisementDetail>(`/advertisements/${id}`);
  return data;
}

export interface UpdateAdvertisementInput {
  title?: string;
  script_text?: string;
  cta_text?: string;
  hashtags?: string[];
  duration_seconds?: number;
  status?: Advertisement["status"];
}

export async function updateAdvertisement(id: string, input: UpdateAdvertisementInput): Promise<AdvertisementDetail> {
  const { data } = await api.patch<AdvertisementDetail>(`/advertisements/${id}`, input);
  return data;
}

export async function uploadAdvertisementAsset(
  advertisementId: string,
  assetType: AssetType,
  file: File,
) {
  const formData = new FormData();
  formData.append("asset_type", assetType);
  formData.append("file", file);
  const { data } = await api.post(`/advertisements/${advertisementId}/assets`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteAdvertisementAsset(advertisementId: string, assetId: string): Promise<void> {
  await api.delete(`/advertisements/${advertisementId}/assets/${assetId}`);
}

export async function listAssetsPendingModeration(): Promise<AssetModerationQueueItem[]> {
  const { data } = await api.get<AssetModerationQueueItem[]>("/admin/asset-moderation");
  return data;
}

export async function approveAssetModeration(assetId: string): Promise<AdvertisementAsset> {
  const { data } = await api.post<AdvertisementAsset>(`/admin/asset-moderation/${assetId}/approve`);
  return data;
}

export async function rejectAssetModeration(assetId: string, reason: string): Promise<AdvertisementAsset> {
  const { data } = await api.post<AdvertisementAsset>(`/admin/asset-moderation/${assetId}/reject`, { reason });
  return data;
}
