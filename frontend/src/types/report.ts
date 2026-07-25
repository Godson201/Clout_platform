export type ReportGeneratorMode = "template" | "anthropic";

export interface CampaignReport {
  id: string;
  campaign_id: string;
  narrative: string;
  data_snapshot: Record<string, unknown>;
  generator: ReportGeneratorMode;
  created_at: string;
}
