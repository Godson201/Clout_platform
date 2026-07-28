"use client";

import { useQuery } from "@tanstack/react-query";
import { Megaphone, MessageSquare, TrendingDown, TrendingUp, UserPlus } from "lucide-react";
import Link from "next/link";

import { PlatformDonutChart } from "@/components/charts/platform-donut-chart";
import { ViewsLineChart } from "@/components/charts/views-line-chart";
import { Avatar, AvatarFallback, AvatarGroup, AvatarGroupCount, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getBrandDashboardSummary } from "@/lib/brand-dashboard-api";
import { listNotifications } from "@/lib/notifications-api";
import type { TopCampaign } from "@/types/brand-dashboard";
import type { Notification } from "@/types/notification";

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min${mins === 1 ? "" : "s"} ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function MomBadge({ pct }: { pct: number | null }) {
  if (pct === null) return null;
  const isUp = pct >= 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-medium ${isUp ? "text-success" : "text-destructive"}`}>
      {isUp ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />}
      {isUp ? "+" : ""}
      {pct}% vs last month
    </span>
  );
}

function StatCard({
  label,
  value,
  momPct,
}: {
  label: string;
  value: string;
  momPct: number | null;
}) {
  return (
    <Card className="premium-card-hover">
      <CardContent className="space-y-1.5 py-1">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-semibold">{value}</p>
        <MomBadge pct={momPct} />
      </CardContent>
    </Card>
  );
}

function campaignStatusVariant(status: string) {
  if (status === "completed") return "success" as const;
  if (status === "active" || status === "listed") return "secondary" as const;
  if (status === "cancelled") return "destructive" as const;
  return "outline" as const;
}

function TopCampaignsTable({ campaigns }: { campaigns: TopCampaign[] }) {
  if (campaigns.length === 0) {
    return <p className="py-10 text-center text-sm text-muted-foreground">No campaigns with tracked views yet.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Campaign</TableHead>
          <TableHead>Platforms</TableHead>
          <TableHead>Influencer(s)</TableHead>
          <TableHead>Views</TableHead>
          <TableHead>Progress</TableHead>
          <TableHead className="text-right">Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {campaigns.map((c) => (
          <TableRow key={c.campaign_id}>
            <TableCell className="max-w-40 truncate font-medium">
              <Link href={`/brand/campaigns/${c.campaign_id}`} className="hover:underline">
                {c.title}
              </Link>
            </TableCell>
            <TableCell className="capitalize text-muted-foreground">{c.platforms.join(", ")}</TableCell>
            <TableCell>
              {c.influencer_avatars.length === 0 ? (
                <span className="text-muted-foreground">—</span>
              ) : (
                <AvatarGroup>
                  {c.influencer_avatars.slice(0, 3).map((url, i) => (
                    <Avatar key={i} size="sm">
                      {url && <AvatarImage src={url} alt="" />}
                      <AvatarFallback>
                        <UserPlus className="size-3" />
                      </AvatarFallback>
                    </Avatar>
                  ))}
                  {c.influencer_avatars.length > 3 && (
                    <AvatarGroupCount className="size-6 text-xs">+{c.influencer_avatars.length - 3}</AvatarGroupCount>
                  )}
                </AvatarGroup>
              )}
            </TableCell>
            <TableCell>{c.total_views.toLocaleString()}</TableCell>
            <TableCell>{c.progress_pct}%</TableCell>
            <TableCell className="text-right">
              <Badge variant={campaignStatusVariant(c.status)} className="capitalize">
                {c.status}
              </Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ActivityIcon({ type }: { type: Notification["type"] }) {
  if (type === "slot_claimed") return <UserPlus className="size-4 text-primary" />;
  if (type === "payment_confirmed") return <TrendingUp className="size-4 text-success" />;
  if (type === "influencer_post_published") return <Megaphone className="size-4 text-primary" />;
  return <MessageSquare className="size-4 text-primary" />;
}

function RecentActivity() {
  const { data: notifications } = useQuery({
    queryKey: ["notifications"],
    queryFn: listNotifications,
    refetchInterval: 20_000,
  });
  const items = notifications?.slice(0, 6) ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">Nothing happening yet.</p>
        ) : (
          <ul className="space-y-4">
            {items.map((n) => (
              <li key={n.id} className="flex items-start gap-3">
                <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-muted">
                  <ActivityIcon type={n.type} />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm">{n.title}</p>
                  <p className="text-xs text-muted-foreground">{relativeTime(n.created_at)}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function BrandOverviewStats() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["brands", "dashboard-summary"],
    queryFn: getBrandDashboardSummary,
  });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading dashboard...</p>;
  if (error || !data) return <p className="text-sm text-destructive">Could not load dashboard stats.</p>;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Campaigns" value={data.total_campaigns.toLocaleString()} momPct={data.total_campaigns_mom_pct} />
        <StatCard label="Total Views" value={data.total_views.toLocaleString()} momPct={data.total_views_mom_pct} />
        <StatCard label="Total Engagements" value={data.total_engagement.toLocaleString()} momPct={data.total_engagement_mom_pct} />
        <StatCard
          label="Total Spent"
          value={`${data.currency} ${data.total_spent.toLocaleString()}`}
          momPct={data.total_spent_mom_pct}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Views Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <ViewsLineChart data={data.views_over_time} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Views by Platform</CardTitle>
          </CardHeader>
          <CardContent>
            <PlatformDonutChart viewsByPlatform={data.views_by_platform} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top Performing Campaigns</CardTitle>
          </CardHeader>
          <CardContent>
            <TopCampaignsTable campaigns={data.top_campaigns} />
          </CardContent>
        </Card>
        <RecentActivity />
      </div>
    </div>
  );
}
