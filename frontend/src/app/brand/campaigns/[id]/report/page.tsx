"use client";

/* Natural-language explanatory copy intentionally contains contractions. */
/* eslint-disable react/no-unescaped-entities */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import type { AxiosError } from "axios";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { generateCampaignReport, getLatestCampaignReport } from "@/lib/campaigns-api";

function CampaignReportView({ campaignId }: { campaignId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: report, isLoading } = useQuery({
    queryKey: ["campaign", campaignId, "report"],
    queryFn: () => getLatestCampaignReport(campaignId),
    retry: false,
  });

  const generateMutation = useMutation({
    mutationFn: () => generateCampaignReport(campaignId),
    onSuccess: (newReport) => queryClient.setQueryData(["campaign", campaignId, "report"], newReport),
  });

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.push(`/brand/campaigns/${campaignId}/analytics`)}>
        ← Back to analytics
      </Button>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Campaign report</CardTitle>
          <Button size="sm" onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
            {generateMutation.isPending ? "Generating..." : report ? "Regenerate" : "Generate report"}
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}

          {generateMutation.isError && (
            <p className="text-sm text-destructive">
              {(generateMutation.error as AxiosError<{ detail?: string }>)?.response?.data?.detail ??
                "Could not generate a report."}
            </p>
          )}

          {!isLoading && !report && !generateMutation.data && (
            <p className="text-sm text-muted-foreground">
              No report has been generated yet — every number it contains comes straight from this campaign's
              verified analytics and comment data, never estimated.
            </p>
          )}

          {(generateMutation.data ?? report) && (
            <div className="space-y-3">
              <Badge variant="secondary" className="capitalize">
                {(generateMutation.data ?? report)!.generator === "anthropic" ? "AI-written" : "Auto-generated"}
              </Badge>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{(generateMutation.data ?? report)!.narrative}</p>
              <p className="text-xs text-muted-foreground">
                Generated {new Date((generateMutation.data ?? report)!.created_at).toLocaleString()}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function CampaignReportPage() {
  const params = useParams<{ id: string }>();
  return (
    <RequireUserType allow={["brand"]}>
      <DashboardShell title="Campaign report">
        <CampaignReportView campaignId={params.id} />
      </DashboardShell>
    </RequireUserType>
  );
}
