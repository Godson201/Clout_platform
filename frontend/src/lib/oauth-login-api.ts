import { api } from "@/lib/api";
import type { AccessTokenResponse, UserType } from "@/types/auth";

export interface OAuthLoginResponse extends AccessTokenResponse {
  created: boolean;
}

export async function getOAuthAuthorizationUrl(provider: string, userType?: UserType): Promise<string> {
  const { data } = await api.get<{ authorization_url: string }>(`/auth/oauth/${provider}/authorize`, {
    params: userType ? { user_type: userType } : {},
  });
  return data.authorization_url;
}

export async function completeOAuthLogin(provider: string, code: string, state: string): Promise<OAuthLoginResponse> {
  const { data } = await api.post<OAuthLoginResponse>(`/auth/oauth/${provider}/callback`, { code, state });
  return data;
}
