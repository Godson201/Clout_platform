import { api } from "@/lib/api";
import type { AssetComment, AssetLikeStatus } from "@/types/asset-comment";

export async function listAssetComments(assetId: string): Promise<AssetComment[]> {
  const { data } = await api.get<AssetComment[]>(`/assets/${assetId}/comments`);
  return data;
}

export async function addAssetComment(assetId: string, body: string): Promise<AssetComment> {
  const { data } = await api.post<AssetComment>(`/assets/${assetId}/comments`, { body });
  return data;
}

export async function getAssetLikeStatus(assetId: string): Promise<AssetLikeStatus> {
  const { data } = await api.get<AssetLikeStatus>(`/assets/${assetId}/like`);
  return data;
}

export async function toggleAssetLike(assetId: string): Promise<AssetLikeStatus> {
  const { data } = await api.post<AssetLikeStatus>(`/assets/${assetId}/like`);
  return data;
}
