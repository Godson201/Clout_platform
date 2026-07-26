import { api } from "@/lib/api";
import type { AccessTokenResponse, User } from "@/types/auth";

export interface BrandRegisterInput {
  email: string;
  password: string;
  business_name: string;
  sector?: string;
  province?: string;
  location?: string;
  admin_sector?: string;
  admin_cell?: string;
  admin_village?: string;
  address_detail?: string;
  phone_number?: string;
  security_question?: string;
  security_answer?: string;
}

export interface InfluencerRegisterInput {
  email: string;
  password: string;
  display_name: string;
  username: string;
  province?: string;
  location?: string;
  admin_sector?: string;
  admin_cell?: string;
  admin_village?: string;
  address_detail?: string;
  sector?: string;
  phone_number?: string;
  security_question?: string;
  security_answer?: string;
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

export async function verifyEmail(token: string): Promise<void> {
  await api.post("/auth/verify-email", { token });
}

export async function resendVerificationEmail(): Promise<void> {
  await api.post("/auth/resend-verification");
}

export async function forgotPassword(email: string): Promise<void> {
  await api.post("/auth/forgot-password", { email });
}

export async function getPasswordResetPrompt(token: string): Promise<{ security_question: string | null }> {
  const { data } = await api.get<{ security_question: string | null }>(
    `/auth/reset-password/${encodeURIComponent(token)}`,
  );
  return data;
}

export async function resetPassword(input: {
  token: string;
  new_password: string;
  security_answer?: string;
}): Promise<void> {
  await api.post("/auth/reset-password", input);
}

export async function changePassword(input: { current_password: string; new_password: string }): Promise<void> {
  await api.post("/users/me/change-password", input);
}
