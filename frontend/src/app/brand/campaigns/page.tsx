"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listCampaigns } from "@/lib/campaigns-api";
import type { CampaignStatus } from "@/types/campaign";

function statusVariant(status: CampaignStatus) {
  if (status === "listed" || status === "active" || status === "completed") return "default" as const;
  if (status === "cancelled") return "destructive" as const;
  return "secondary" as const;
}

function CampaignList() {
  const { data, isLoading, error } = useQuery({ queryKey: ["campaigns"], queryFn: () => listCampaigns() });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading campaigns...</p>;
  if (error) return <p className="text-sm text-destructive">Could not load campaigns.</p>;

  if (!data || data.items.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <p className="mb-4 text-sm text-muted-foreground">No campaigns yet.</p>
          <Button render={<Link href="/brand/campaigns/new" />}>Create a campaign</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {data.items.map((c) => (
        <Link key={c.id} href={`/brand/campaigns/${c.id}`}>
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base capitalize">{c.platforms.join(", ")}</CardTitle>
              <Badge variant={statusVariant(c.status)} className="capitalize">
                {c.status.replace("_", " ")}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>{c.target_views.toLocaleString()} target views / platform</p>
              <p>{c.slot_count} influencers / platform · {c.tier} tier</p>
              <p className="font-medium text-foreground">
                {Number(c.total_brand_payment).toLocaleString()} {c.currency}
              </p>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

export default function BrandCampaignsPage() {
  return (
    <RequireUserType allow={["brand"]}>
      <DashboardShell title="Campaigns">
        <div className="mb-6 flex justify-end">
          <Button render={<Link href="/brand/campaigns/new" />}>+ New campaign</Button>
        </div>
        <CampaignList />
      </DashboardShell>
    </RequireUserType>
  );
}
