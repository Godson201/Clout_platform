import { api } from "@/lib/api";
import type { Brand, Influencer } from "@/types/auth";

export async function uploadBrandLogo(file: File): Promise<Brand> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<Brand>("/brands/me/logo", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function uploadInfluencerPicture(file: File): Promise<Influencer> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<Influencer>("/influencers/me/picture", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
