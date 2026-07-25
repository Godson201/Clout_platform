import { api } from "@/lib/api";
import type { AwaitingSettlementItem } from "@/types/analytics";
import type { CampaignSlot } from "@/types/campaign";

export async function listAwaitingSettlement(): Promise<AwaitingSettlementItem[]> {
  const { data } = await api.get<AwaitingSettlementItem[]>("/admin/slots/awaiting-settlement");
  return data;
}

export async function settleSlot(slotId: string, deliveredPct: string): Promise<CampaignSlot> {
  const { data } = await api.post<CampaignSlot>(`/admin/slots/${slotId}/settle`, { delivered_pct: deliveredPct });
  return data;
}
