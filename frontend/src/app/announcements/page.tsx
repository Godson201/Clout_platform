"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  createAnnouncement,
  listAllAnnouncementsAdmin,
  listAnnouncements,
  setAnnouncementActive,
} from "@/lib/announcements-api";
import { useAuthStore } from "@/store/auth-store";
import type { Announcement, AnnouncementAudience } from "@/types/announcement";

function AnnouncementCard({ announcement, adminControls }: { announcement: Announcement; adminControls?: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base">{announcement.title}</CardTitle>
        <div className="flex items-center gap-1">
          {announcement.audience !== "all" && (
            <Badge variant="outline" className="capitalize">
              {announcement.audience}
            </Badge>
          )}
          {!announcement.is_active && <Badge variant="secondary">Retracted</Badge>}
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="whitespace-pre-wrap text-sm text-muted-foreground">{announcement.body}</p>
        <p className="text-xs text-muted-foreground">{new Date(announcement.created_at).toLocaleString()}</p>
        {adminControls}
      </CardContent>
    </Card>
  );
}

function ComposerCard() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState<AnnouncementAudience>("all");

  const mutation = useMutation({
    mutationFn: () => createAnnouncement({ title, body, audience }),
    onSuccess: () => {
      setTitle("");
      setBody("");
      setAudience("all");
      queryClient.invalidateQueries({ queryKey: ["announcements", "admin"] });
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>New announcement</CardTitle>
        <CardDescription>Broadcast a message to brands, influencers, or everyone.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label>Title</Label>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>Message</Label>
          <Textarea value={body} onChange={(e) => setBody(e.target.value)} rows={4} />
        </div>
        <div className="space-y-2">
          <Label>Audience</Label>
          <Select value={audience} onValueChange={(v) => setAudience((v as AnnouncementAudience) ?? "all")}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Everyone</SelectItem>
              <SelectItem value="brands">Brands only</SelectItem>
              <SelectItem value="influencers">Influencers only</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || title.trim().length < 2 || body.trim().length < 2}
        >
          {mutation.isPending ? "Posting..." : "Post announcement"}
        </Button>
      </CardContent>
    </Card>
  );
}

function AdminAnnouncementsView() {
  const queryClient = useQueryClient();
  const { data: announcements } = useQuery({ queryKey: ["announcements", "admin"], queryFn: listAllAnnouncementsAdmin });

  const toggleMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) => setAnnouncementActive(id, isActive),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["announcements", "admin"] }),
  });

  return (
    <div className="space-y-6">
      <ComposerCard />
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground">All announcements</h2>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {announcements?.map((a) => (
            <AnnouncementCard
              key={a.id}
              announcement={a}
              adminControls={
                <Button
                  size="xs"
                  variant="outline"
                  onClick={() => toggleMutation.mutate({ id: a.id, isActive: !a.is_active })}
                  disabled={toggleMutation.isPending}
                >
                  {a.is_active ? "Retract" : "Reactivate"}
                </Button>
              }
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function FeedView() {
  const { data: announcements, isLoading } = useQuery({ queryKey: ["announcements"], queryFn: listAnnouncements });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading announcements...</p>;
  if (!announcements || announcements.length === 0) {
    return <p className="text-sm text-muted-foreground">No announcements right now.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {announcements.map((a) => (
        <AnnouncementCard key={a.id} announcement={a} />
      ))}
    </div>
  );
}

export default function AnnouncementsPage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.user_type === "admin";

  return (
    <RequireUserType allow={["brand", "influencer", "admin"]}>
      <DashboardShell title="Announcements">
        {isAdmin ? <AdminAnnouncementsView /> : <FeedView />}
      </DashboardShell>
    </RequireUserType>
  );
}
