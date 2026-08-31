"use client";

/* Natural-language explanatory copy intentionally contains contractions. */
/* eslint-disable react/no-unescaped-entities */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getCampaignAnalytics } from "@/lib/campaigns-api";

function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  );
}

function CampaignAnalyticsView({ campaignId }: { campaignId: string }) {
  const router = useRouter();
  const { data, isLoading, error } = useQuery({
    queryKey: ["campaign", campaignId, "analytics"],
    queryFn: () => getCampaignAnalytics(campaignId),
    refetchInterval: 15000,
  });

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.push(`/brand/campaigns/${campaignId}`)}>
        ← Back to campaign
      </Button>

      {isLoading && <p className="text-sm text-muted-foreground">Loading analytics...</p>}
      {error && <p className="text-sm text-destructive">Could not load analytics for this campaign.</p>}

      {data && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Overview</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-6 sm:grid-cols-4">
              <StatTile label="Verified views" value={data.total_verified_views.toLocaleString()} />
              <StatTile label="Target views" value={data.total_target_views.toLocaleString()} />
              <StatTile label="Progress" value={`${data.progress_pct}%`} />
              <StatTile label="Total engagement" value={data.total_engagement.toLocaleString()} />
            </CardContent>
          </Card>

          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Views by platform</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {Object.entries(data.views_by_platform).length === 0 && (
                  <p className="text-muted-foreground">No verified views yet.</p>
                )}
                {Object.entries(data.views_by_platform).map(([platform, views]) => (
                  <div key={platform} className="flex justify-between">
                    <span className="capitalize">
                      {platform}
                      {platform === data.top_platform && " 🏆"}
                    </span>
                    <span className="font-medium">{views.toLocaleString()}</span>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Slot status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {Object.entries(data.slot_status_counts).map(([status, count]) => (
                  <div key={status} className="flex justify-between">
                    <span className="capitalize">{status.replace("_", " ")}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Influencer performance</CardTitle>
            </CardHeader>
            <CardContent>
              {data.influencer_performance.length === 0 ? (
                <p className="text-sm text-muted-foreground">No verified metrics yet.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Influencer</TableHead>
                      <TableHead>Platform</TableHead>
                      <TableHead>Views</TableHead>
                      <TableHead>Likes</TableHead>
                      <TableHead>Comments</TableHead>
                      <TableHead>Shares</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.influencer_performance.map((p) => (
                      <TableRow key={`${p.influencer_id}-${p.platform}`}>
                        <TableCell>
                          @{p.username}
                          {p.username === data.top_influencer_username && " 🏆"}
                        </TableCell>
                        <TableCell className="capitalize">{p.platform}</TableCell>
                        <TableCell>{p.views.toLocaleString()}</TableCell>
                        <TableCell>{p.likes.toLocaleString()}</TableCell>
                        <TableCell>{p.comments.toLocaleString()}</TableCell>
                        <TableCell>{p.shares.toLocaleString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Audience sentiment</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {data.comment_summary.total_comments === 0 ? (
                <p className="text-muted-foreground">No comments tracked yet.</p>
              ) : (
                <>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Comments tracked</span>
                    <span className="font-medium">{data.comment_summary.total_comments}</span>
                  </div>
                  {data.comment_summary.average_sentiment_score !== null && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Average sentiment</span>
                      <span className="font-medium">{data.comment_summary.average_sentiment_score}</span>
                    </div>
                  )}
                  {Object.entries(data.comment_summary.category_counts).map(([category, count]) => (
                    <div key={category} className="flex justify-between">
                      <span className="capitalize text-muted-foreground">{category}</span>
                      <span className="font-medium">{count}</span>
                    </div>
                  ))}
                  {data.comment_summary.sample_questions.length > 0 && (
                    <div className="pt-2">
                      <p className="mb-1 text-muted-foreground">Questions worth a reply</p>
                      <ul className="list-inside list-disc space-y-1">
                        {data.comment_summary.sample_questions.map((q, i) => (
                          <li key={i}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Report</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Generate a persuasive summary of this campaign's performance — every number in it comes straight
                from the verified data above.
              </p>
              <Button size="sm" render={<Link href={`/brand/campaigns/${campaignId}/report`} />}>
                View report
              </Button>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

export default function CampaignAnalyticsPage() {
  const params = useParams<{ id: string }>();
  return (
    <RequireUserType allow={["brand"]}>
      <DashboardShell title="Campaign analytics">
        <CampaignAnalyticsView campaignId={params.id} />
      </DashboardShell>
    </RequireUserType>
  );
}
