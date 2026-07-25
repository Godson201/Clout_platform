"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import type { AxiosError } from "axios";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cancelCampaign, fundCampaign, getCampaign, getCampaignPayment } from "@/lib/campaigns-api";
import type { CampaignSlot } from "@/types/campaign";
import type { Payment } from "@/types/payment";

function slotStatusVariant(status: CampaignSlot["status"]) {
  if (status === "open") return "secondary" as const;
  if (status === "cancelled" || status === "failed") return "destructive" as const;
  return "default" as const;
}

function paymentStatusVariant(status: Payment["status"]) {
  if (status === "successful") return "default" as const;
  if (status === "failed") return "destructive" as const;
  return "secondary" as const;
}

function errorDetail(error: unknown): string | null {
  const detail = (error as AxiosError<{ detail?: string }> | null)?.response?.data?.detail;
  return detail ?? null;
}

function CampaignDetail({ campaignId }: { campaignId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [fundPhone, setFundPhone] = useState("");
  const [cancelPhone, setCancelPhone] = useState("");

  const { data: campaign, isLoading, error } = useQuery({
    queryKey: ["campaign", campaignId],
    queryFn: () => getCampaign(campaignId),
  });

  const hasInitiatedPayment = campaign?.status === "pending_funding" || campaign?.status === "listed" || campaign?.status === "active";

  const { data: payment } = useQuery({
    queryKey: ["campaign", campaignId, "payment"],
    queryFn: () => getCampaignPayment(campaignId),
    enabled: !!hasInitiatedPayment,
    retry: false,
    // Every GET re-polls the provider server-side (see the backend endpoint) —
    // this is the same reconciliation path a scheduled Celery task would run,
    // just triggered by the brand having this page open.
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 3000 : false),
  });

  const fundMutation = useMutation({
    mutationFn: () => fundCampaign(campaignId, fundPhone),
    onSuccess: ({ campaign: updated }) => {
      queryClient.setQueryData(["campaign", campaignId], updated);
      queryClient.invalidateQueries({ queryKey: ["campaign", campaignId, "payment"] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelCampaign(campaignId, cancelPhone || undefined),
    onSuccess: (updated) => queryClient.setQueryData(["campaign", campaignId], updated),
  });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading campaign...</p>;
  if (error || !campaign) return <p className="text-sm text-destructive">Could not load this campaign.</p>;

  const canFund = campaign.status === "draft" || campaign.status === "pending_funding";
  const canCancel = campaign.status !== "completed" && campaign.status !== "cancelled";
  const hasEscrow = campaign.escrow_balance !== null && Number(campaign.escrow_balance) > 0;
  const paymentIsPending = payment?.status === "pending";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => router.push("/brand/campaigns")}>
          ← Back to campaigns
        </Button>
        {campaign.slots.length > 0 && (
          <Button size="sm" variant="outline" render={<Link href={`/brand/campaigns/${campaignId}/analytics`} />}>
            View analytics
          </Button>
        )}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="capitalize">{campaign.platforms.join(", ")} campaign</CardTitle>
          <Badge className="capitalize">{campaign.status.replace("_", " ")}</Badge>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Target views / platform</dt>
              <dd className="font-medium">{campaign.target_views.toLocaleString()}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Tier</dt>
              <dd className="font-medium capitalize">{campaign.tier}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Influencers / platform</dt>
              <dd className="font-medium">{campaign.slot_count}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Performance window</dt>
              <dd className="font-medium">{campaign.performance_window_days} days</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Base price (escrow)</dt>
              <dd className="font-medium">
                {Number(campaign.base_price).toLocaleString()} {campaign.currency}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Total (incl. {Number(campaign.brand_fee_pct) * 100}% fee)</dt>
              <dd className="font-medium">
                {Number(campaign.total_brand_payment).toLocaleString()} {campaign.currency}
              </dd>
            </div>
            {hasEscrow && (
              <div>
                <dt className="text-muted-foreground">Escrow balance</dt>
                <dd className="font-medium">
                  {Number(campaign.escrow_balance).toLocaleString()} {campaign.currency}
                </dd>
              </div>
            )}
          </dl>

          {payment && (
            <div className="mt-4 flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">MoMo payment:</span>
              <Badge variant={paymentStatusVariant(payment.status)} className="capitalize">
                {payment.status}
              </Badge>
              {paymentIsPending && (
                <span className="text-muted-foreground">Waiting for MTN MoMo to confirm the request to pay...</span>
              )}
              {payment.status === "failed" && payment.failure_reason && (
                <span className="text-destructive">{payment.failure_reason}</span>
              )}
            </div>
          )}

          {(fundMutation.isError || cancelMutation.isError) && (
            <p className="mt-4 text-sm text-destructive">
              {errorDetail(fundMutation.error) ?? errorDetail(cancelMutation.error) ?? "Something went wrong."}
            </p>
          )}

          <div className="mt-4 space-y-3">
            {canFund && (
              <div className="flex flex-wrap items-end gap-2">
                <div className="space-y-1">
                  <Label htmlFor="fund-phone">MoMo phone number</Label>
                  <Input
                    id="fund-phone"
                    placeholder="07XXXXXXXX"
                    value={fundPhone}
                    onChange={(e) => setFundPhone(e.target.value)}
                    className="w-48"
                  />
                </div>
                <Button onClick={() => fundMutation.mutate()} disabled={fundMutation.isPending || !fundPhone}>
                  {fundMutation.isPending ? "Requesting..." : `Pay ${Number(campaign.total_brand_payment).toLocaleString()} ${campaign.currency} via MoMo`}
                </Button>
              </div>
            )}
            {canCancel && (
              <div className="flex flex-wrap items-end gap-2">
                {hasEscrow && (
                  <div className="space-y-1">
                    <Label htmlFor="cancel-phone">Refund MoMo number</Label>
                    <Input
                      id="cancel-phone"
                      placeholder="07XXXXXXXX"
                      value={cancelPhone}
                      onChange={(e) => setCancelPhone(e.target.value)}
                      className="w-48"
                    />
                  </div>
                )}
                <Button
                  variant="outline"
                  onClick={() => cancelMutation.mutate()}
                  disabled={cancelMutation.isPending || (hasEscrow && !cancelPhone)}
                >
                  {cancelMutation.isPending ? "Cancelling..." : "Cancel campaign"}
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground">
          Slots ({campaign.slots.length})
        </h2>
        {campaign.slots.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Slots are generated once MoMo confirms funding and the campaign is listed on the marketplace.
          </p>
        )}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {campaign.slots.map((slot) => (
            <Card key={slot.id}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm capitalize">{slot.platform}</CardTitle>
                <div className="flex items-center gap-1">
                  {slot.recovery_generation > 0 && (
                    <Badge
                      variant="outline"
                      title="This slot's budget was recycled from an earlier slot's delivery shortfall"
                    >
                      Recovery gen {slot.recovery_generation}
                    </Badge>
                  )}
                  <Badge variant={slotStatusVariant(slot.status)} className="capitalize">
                    {slot.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                <p>{slot.target_views.toLocaleString()} views</p>
                <p>
                  {Number(slot.budget_allocated).toLocaleString()} {campaign.currency}
                </p>
                {slot.delivered_pct !== null && <p>Delivered: {Number(slot.delivered_pct).toFixed(0)}%</p>}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function BrandCampaignDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <RequireUserType allow={["brand"]}>
      <DashboardShell title="Campaign detail">
        <CampaignDetail campaignId={params.id} />
      </DashboardShell>
    </RequireUserType>
  );
}
