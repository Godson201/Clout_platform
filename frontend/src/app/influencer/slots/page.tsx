"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listMySlots } from "@/lib/campaigns-api";
import type { MySlot } from "@/types/campaign";

const ACTIVE_STATUSES = new Set(["claimed", "published", "tracking"]);

function statusVariant(status: MySlot["status"]) {
  if (status === "completed") return "default" as const;
  if (status === "failed" || status === "cancelled") return "destructive" as const;
  return "secondary" as const;
}

function MySlotsList() {
  const { data, isLoading, error } = useQuery({ queryKey: ["slots", "mine"], queryFn: listMySlots });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading your slots...</p>;
  if (error) return <p className="text-sm text-destructive">Could not load your slots.</p>;
  if (!data || data.length === 0) {
    return <p className="text-sm text-muted-foreground">You haven&apos;t claimed any slots yet.</p>;
  }

  const activeCount = data.filter((s) => ACTIVE_STATUSES.has(s.status)).length;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {activeCount} of 5 active slots in use.
      </p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data.map((slot) => (
          <Card key={slot.id}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-base">{slot.advertisement_title}</CardTitle>
              <div className="flex items-center gap-1">
                {slot.recovery_generation > 0 && (
                  <Badge variant="outline" title="This slot was recycled from an earlier delivery shortfall">
                    Recovered
                  </Badge>
                )}
                <Badge variant={statusVariant(slot.status)} className="capitalize">
                  {slot.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>{slot.brand_name}</p>
              <p className="capitalize">{slot.platform} · {slot.tier} tier</p>
              <p>{slot.target_views.toLocaleString()} views target</p>
              <p className="font-medium text-foreground">
                {Number(slot.budget_allocated).toLocaleString()} budget
              </p>
              {slot.delivered_pct !== null && (
                <p>Delivered: {Number(slot.delivered_pct).toFixed(0)}%</p>
              )}
              <Button size="sm" variant="outline" render={<Link href={`/influencer/slots/${slot.id}`} />}>
                View / post
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function MySlotsPage() {
  return (
    <RequireUserType allow={["influencer"]}>
      <DashboardShell title="My Slots">
        <MySlotsList />
      </DashboardShell>
    </RequireUserType>
  );
}
