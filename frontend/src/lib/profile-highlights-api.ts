import { api } from "@/lib/api";
import type { HighlightCategory, ProfileHighlight, PublicBrandProfile, PublicInfluencerProfile } from "@/types/profile-highlight";

export async function listMyHighlights(): Promise<ProfileHighlight[]> {
  const { data } = await api.get<ProfileHighlight[]>("/profile-highlights/me");
  return data;
}

export async function createHighlight(input: {
  category: HighlightCategory;
  title: string;
  subtitle?: string;
  occurred_on?: string;
  description?: string;
}): Promise<ProfileHighlight> {
  const { data } = await api.post<ProfileHighlight>("/profile-highlights", input);
  return data;
}

export async function deleteHighlight(id: string): Promise<void> {
  await api.delete(`/profile-highlights/${id}`);
}

export async function getPublicBrandProfile(brandId: string): Promise<PublicBrandProfile> {
  const { data } = await api.get<PublicBrandProfile>(`/brands/${brandId}/public`);
  return data;
}

export async function getPublicInfluencerProfile(influencerId: string): Promise<PublicInfluencerProfile> {
  const { data } = await api.get<PublicInfluencerProfile>(`/influencers/${influencerId}/public`);
  return data;
}
