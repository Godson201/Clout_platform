"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { useState } from "react";

import { AssetPreview, assetCaption } from "@/components/advertisements/asset-preview";
import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { approveAssetModeration, listAssetsPendingModeration, rejectAssetModeration } from "@/lib/advertisements-api";
import type { AssetModerationQueueItem } from "@/types/advertisement";

function QueueItem({ item }: { item: AssetModerationQueueItem }) {
  const queryClient = useQueryClient();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin", "asset-moderation"] });

  const approveMutation = useMutation({
    mutationFn: () => approveAssetModeration(item.id),
    onSuccess: invalidate,
  });
  const rejectMutation = useMutation({
    mutationFn: () => rejectAssetModeration(item.id, reason),
    onSuccess: () => {
      setRejecting(false);
      setReason("");
      invalidate();
    },
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-sm">{item.brand_name}</CardTitle>
          <p className="text-xs text-muted-foreground">
            {item.advertisement_title} · <span className="capitalize">{item.asset_type}</span>
          </p>
        </div>
        <Badge variant="warning">Pending review</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <AssetPreview asset={item} />
        <p className="text-xs text-muted-foreground">{assetCaption(item)}</p>

        {(approveMutation.isError || rejectMutation.isError) && (
          <p className="text-sm text-destructive">
            {((approveMutation.error ?? rejectMutation.error) as AxiosError<{ detail?: string }> | undefined)
              ?.response?.data?.detail ?? "Something went wrong."}
          </p>
        )}

        {rejecting ? (
          <div className="space-y-2">
            <Textarea
              placeholder="Reason for rejecting (shown to the brand)..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="destructive"
                disabled={reason.trim().length < 2 || rejectMutation.isPending}
                onClick={() => rejectMutation.mutate()}
              >
                {rejectMutation.isPending ? "Rejecting..." : "Confirm rejection"}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setRejecting(false)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2">
            <Button size="sm" disabled={approveMutation.isPending} onClick={() => approveMutation.mutate()}>
              {approveMutation.isPending ? "Approving..." : "Approve & notify influencers"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setRejecting(true)}>
              Reject
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MediaReviewQueue() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "asset-moderation"],
    queryFn: listAssetsPendingModeration,
    refetchInterval: 15000,
  });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading...</p>;
  if (!data || data.length === 0) {
    return <p className="text-sm text-muted-foreground">Nothing awaiting review right now.</p>;
  }

  return (
    <div className="space-y-4">
      {data.map((item) => (
        <QueueItem key={item.id} item={item} />
      ))}
    </div>
  );
}

export default function AdminMediaReviewPage() {
  return (
    <RequireUserType allow={["admin"]}>
      <DashboardShell title="Media review">
        <div className="space-y-6">
          <p className="text-sm text-muted-foreground">
            Brand-uploaded video, photo, and audio content waits here once processed and playable. Approving broadcasts
            a notification to every influencer; rejecting sends the brand your reason and keeps it private.
          </p>
          <MediaReviewQueue />
        </div>
      </DashboardShell>
    </RequireUserType>
  );
}
