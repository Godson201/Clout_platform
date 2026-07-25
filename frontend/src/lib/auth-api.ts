import { api } from "@/lib/api";
import type { AccessTokenResponse, User } from "@/types/auth";

export interface BrandRegisterInput {
  email: string;
  password: string;
  business_name: string;
  sector?: string;
  location?: string;
  phone_number?: string;
}

export interface InfluencerRegisterInput {
  email: string;
  password: string;
  display_name: string;
  username: string;
  location?: string;
  sector?: string;
  phone_number?: string;
}

export async function registerBrand(input: BrandRegisterInput): Promise<AccessTokenResponse> {
  const { data } = await api.post<AccessTokenResponse>("/auth/register/brand", input);
  return data;
}

export async function registerInfluencer(input: InfluencerRegisterInput): Promise<AccessTokenResponse> {
  const { data } = await api.post<AccessTokenResponse>("/auth/register/influencer", input);
  return data;
}

export async function login(email: string, password: string): Promise<AccessTokenResponse> {
  const { data } = await api.post<AccessTokenResponse>("/auth/login", { email, password });
  return data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/users/me");
  return data;
}
