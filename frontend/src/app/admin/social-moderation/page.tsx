"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { listArchivedSocialPosts, listSocialReports, resolveSocialReport, restoreSocialPost, type SocialReportQueueItem } from "@/lib/social-moderation-api";

function errorDetail(error: unknown) {
  return (error as AxiosError<{ detail?: string }> | undefined)?.response?.data?.detail ?? "The moderation action could not be completed.";
}

function ReportCard({ report }: { report: SocialReportQueueItem }) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin", "social-moderation"] });
  const dismiss = useMutation({ mutationFn: () => resolveSocialReport(report.report_id, false, note), onSuccess: invalidate });
  const archive = useMutation({ mutationFn: () => resolveSocialReport(report.report_id, true, note), onSuccess: invalidate });
  const error = dismiss.error ?? archive.error;
  return <Card><CardHeader className="flex flex-row items-start justify-between gap-3"><div><CardTitle className="text-sm">Reported public post</CardTitle><p className="mt-1 text-xs text-muted-foreground">Reported {new Date(report.created_at).toLocaleString()}</p></div><Badge variant="warning" className="capitalize">{report.reason}</Badge></CardHeader><CardContent className="space-y-3"><p className="rounded-md border bg-muted/30 p-3 whitespace-pre-wrap text-sm">{report.body}</p>{report.details && <p className="text-sm text-muted-foreground">Reporter detail: {report.details}</p>}<Textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={1000} placeholder="Internal moderation note (stored in the audit log)..." />{error && <p className="text-sm text-destructive">{errorDetail(error)}</p>}<div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => dismiss.mutate()} disabled={dismiss.isPending || archive.isPending}>{dismiss.isPending ? "Resolving..." : "Resolve — keep post"}</Button><Button size="sm" variant="destructive" onClick={() => archive.mutate()} disabled={dismiss.isPending || archive.isPending}>{archive.isPending ? "Archiving..." : "Archive post & resolve"}</Button></div></CardContent></Card>;
}

function ModerationQueue() {
  const reports = useQuery({ queryKey: ["admin", "social-moderation", "reports"], queryFn: listSocialReports, refetchInterval: 15_000 });
  if (reports.isLoading) return <p className="text-sm text-muted-foreground">Loading reports...</p>;
  if (!reports.data?.length) return <p className="text-sm text-muted-foreground">No unresolved social reports.</p>;
  return <div className="space-y-4">{reports.data.map((report) => <ReportCard key={report.report_id} report={report} />)}</div>;
}

function ArchivedPosts() {
  const queryClient = useQueryClient();
  const posts = useQuery({ queryKey: ["admin", "social-moderation", "archived"], queryFn: listArchivedSocialPosts });
  const restore = useMutation({ mutationFn: restoreSocialPost, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "social-moderation"] }) });
  if (posts.isLoading) return <p className="text-sm text-muted-foreground">Loading archived posts...</p>;
  if (!posts.data?.length) return <p className="text-sm text-muted-foreground">No posts are archived.</p>;
  return <div className="space-y-3">{posts.data.map((post) => <Card key={post.post_id}><CardContent className="flex flex-col gap-3 pt-5 sm:flex-row sm:items-center sm:justify-between"><p className="whitespace-pre-wrap text-sm">{post.body}</p><Button size="sm" variant="outline" onClick={() => restore.mutate(post.post_id)} disabled={restore.isPending}>{restore.isPending ? "Restoring..." : "Restore post"}</Button></CardContent></Card>)}</div>;
}

export default function AdminSocialModerationPage() {
  const [view, setView] = useState<"reports" | "archived">("reports");
  return <RequireUserType allow={["admin"]}><DashboardShell title="Social moderation"><main className="mx-auto max-w-3xl space-y-5"><div><h1 className="font-semibold">Social moderation</h1><p className="mt-1 text-sm text-muted-foreground">Review community reports, archive unsafe public posts, and restore posts when needed. Every decision is audit logged.</p></div><div className="flex gap-2 border-b"><Button size="sm" variant={view === "reports" ? "default" : "ghost"} onClick={() => setView("reports")}>Reports</Button><Button size="sm" variant={view === "archived" ? "default" : "ghost"} onClick={() => setView("archived")}>Archived posts</Button></div>{view === "reports" ? <ModerationQueue /> : <ArchivedPosts />}</main></DashboardShell></RequireUserType>;
}
