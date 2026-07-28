import { api } from "@/lib/api";
import type { BrandDashboardSummary } from "@/types/brand-dashboard";

export async function getBrandDashboardSummary(): Promise<BrandDashboardSummary> {
  const { data } = await api.get<BrandDashboardSummary>("/brands/me/dashboard-summary");
  return data;
}
