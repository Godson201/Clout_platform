import { api } from "@/lib/api";
import type { AwaitingSettlementItem } from "@/types/analytics";
import type { AuditLog } from "@/types/audit";
import type { User } from "@/types/auth";
import type { CampaignSlot } from "@/types/campaign";

export async function listAwaitingSettlement(): Promise<AwaitingSettlementItem[]> {
  const { data } = await api.get<AwaitingSettlementItem[]>("/admin/slots/awaiting-settlement");
  return data;
}

export async function settleSlot(slotId: string, deliveredPct: string): Promise<CampaignSlot> {
  const { data } = await api.post<CampaignSlot>(`/admin/slots/${slotId}/settle`, { delivered_pct: deliveredPct });
  return data;
}

export async function promoteToAdmin(userId: string): Promise<User> {
  const { data } = await api.post<User>(`/admin/users/${userId}/promote-to-admin`);
  return data;
}

export interface AuditLogPage {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export async function listAuditLogs(page: number, action?: string): Promise<AuditLogPage> {
  const { data } = await api.get<AuditLogPage>("/admin/audit-logs", {
    params: { page, page_size: 25, ...(action ? { action } : {}) },
  });
  return data;
}
