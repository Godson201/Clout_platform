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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { getSlotCreative, listMySlots, publishSlotCreative, uploadSlotCreative } from "@/lib/campaigns-api";
import { crossPost, listCrossPosts, retryCrossPost, type CrossPostDelivery } from "@/lib/social-feed-api";
import {
  createSlotPost,
  getSlotPost,
  getSlotPostComments,
  getSlotPostMetrics,
  listMySocialAccounts,
  submitSlotPostUrl,
} from "@/lib/social-api";
import type { CommentCategory, SocialPost } from "@/types/social";

function errorDetail(error: unknown): string | null {
  return (error as AxiosError<{ detail?: string }> | null)?.response?.data?.detail ?? null;
}

function postStatusVariant(status: SocialPost["status"]) {
  if (status === "published") return "success" as const;
  if (status === "failed" || status === "deleted") return "destructive" as const;
  if (status === "pending") return "warning" as const;
  return "secondary" as const;
}

function categoryVariant(category: CommentCategory) {
  if (category === "complaint" || category === "negative") return "destructive" as const;
  if (category === "positive") return "success" as const;
  return "secondary" as const;
}

function CommentsPanel({ slotId }: { slotId: string }) {
  const { data: comments } = useQuery({
    queryKey: ["slot-post-comments", slotId],
    queryFn: () => getSlotPostComments(slotId),
    refetchInterval: 8000,
  });

  if (!comments || comments.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No comments tracked yet — only platforms CLOUT has live API access to can fetch comments automatically.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {comments.map((c) => (
        <div key={c.id} className="rounded-md border p-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium">@{c.author_handle}</span>
            {c.analysis && (
              <Badge variant={categoryVariant(c.analysis.category)} className="capitalize">
                {c.analysis.category}
              </Badge>
            )}
          </div>
          <p className="mt-1 text-muted-foreground">{c.text}</p>
        </div>
      ))}
    </div>
  );
}

function CreatePostForm({ slotId, platform }: { slotId: string; platform: string }) {
  const queryClient = useQueryClient();
  const [accountId, setAccountId] = useState("");
  const [caption, setCaption] = useState("");

  const { data: accounts } = useQuery({ queryKey: ["social-accounts", "me"], queryFn: listMySocialAccounts });
  const matchingAccounts = (accounts ?? []).filter((a) => a.platform === platform && a.status === "active");

  const mutation = useMutation({
    mutationFn: () => createSlotPost(slotId, accountId, caption),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["slot-post", slotId] }),
  });

  if (matchingAccounts.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Connect a {platform} account before posting to this slot — see{" "}
        <a href="/social-accounts" className="underline">
          Connected accounts
        </a>
        .
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <Label>Connected {platform} account</Label>
        <Select value={accountId} onValueChange={(value) => setAccountId(value ?? "")}>
          <SelectTrigger>
            <SelectValue placeholder="Select an account" />
          </SelectTrigger>
          <SelectContent>
            {matchingAccounts.map((a) => (
              <SelectItem key={a.id} value={a.id}>
                @{a.handle}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1">
        <Label>Caption</Label>
        <Input value={caption} onChange={(e) => setCaption(e.target.value)} placeholder="Caption for this post" />
      </div>
      {mutation.isError && <p className="text-sm text-destructive">{errorDetail(mutation.error)}</p>}
      <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !accountId || !caption}>
        {mutation.isPending ? "Posting..." : "Create post"}
      </Button>
    </div>
  );
}

function ManualSubmitForm({ slotId }: { slotId: string }) {
  const queryClient = useQueryClient();
  const [postUrl, setPostUrl] = useState("");

  const mutation = useMutation({
    mutationFn: () => submitSlotPostUrl(slotId, postUrl),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["slot-post", slotId] }),
  });

  return (
    <div className="space-y-3 rounded-md border p-4">
      <p className="text-sm text-muted-foreground">
        Auto-posting isn&apos;t available on this platform yet — download the ad from the brand toolkit, post it
        yourself, then paste the live post&apos;s URL below.
      </p>
      <div className="space-y-1">
        <Label>Post URL</Label>
        <Input value={postUrl} onChange={(e) => setPostUrl(e.target.value)} placeholder="https://..." />
      </div>
      {mutation.isError && <p className="text-sm text-destructive">{errorDetail(mutation.error)}</p>}
      <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !postUrl}>
        {mutation.isPending ? "Submitting..." : "Submit post URL"}
      </Button>
    </div>
  );
}

function MetricsPanel({ slotId }: { slotId: string }) {
  const { data: snapshots } = useQuery({
    queryKey: ["slot-post-metrics", slotId],
    queryFn: () => getSlotPostMetrics(slotId),
    refetchInterval: 5000,
  });

  if (!snapshots || snapshots.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No metrics yet — only platforms CLOUT has live API access to can report views automatically.
      </p>
    );
  }

  const latest = snapshots[snapshots.length - 1];
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {[
        { label: "Views", value: latest.views },
        { label: "Likes", value: latest.likes },
        { label: "Comments", value: latest.comments },
        { label: "Shares", value: latest.shares ?? "—" },
      ].map((m) => (
        <div key={m.label}>
          <p className="text-xs text-muted-foreground">{m.label}</p>
          <p className="text-lg font-semibold">{typeof m.value === "number" ? m.value.toLocaleString() : m.value}</p>
        </div>
      ))}
    </div>
  );
}

function CreativeWorkspace({ brandName, campaignTitle }: { brandName: string; campaignTitle: string }) {
  const [video, setVideo] = useState<File | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const tooLong = duration !== null && duration > 30;
  return <Card><CardHeader><CardTitle>Create campaign ad</CardTitle></CardHeader><CardContent className="space-y-3"><p className="text-sm text-muted-foreground">Use {brandName}&apos;s approved toolkit creative with your own footage, voice, sound, or editing style for <span className="font-medium text-foreground">{campaignTitle}</span>.</p><div className="rounded-md border border-primary/30 bg-primary/5 p-3 text-sm"><p className="font-medium">Required before publishing</p><p className="text-muted-foreground">Your finished campaign video must be 30 seconds or shorter.</p></div><div className="space-y-1"><Label>Upload your finished video</Label><Input type="file" accept="video/mp4,video/webm,video/quicktime" onChange={(event) => { const file = event.target.files?.[0] ?? null; setVideo(file); setDuration(null); if (file) { const element = document.createElement("video"); element.preload = "metadata"; element.onloadedmetadata = () => { setDuration(element.duration); URL.revokeObjectURL(element.src); }; element.src = URL.createObjectURL(file); } }} /></div>{video && <p className={tooLong ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>{video.name}{duration !== null ? ` · ${duration.toFixed(1)} seconds` : " · checking duration..."}{tooLong ? " — choose a video under 30 seconds." : ""}</p>}<Button variant="outline" disabled={!video || tooLong}>Save draft creative</Button><p className="text-xs text-muted-foreground">Editing inside Clout and final publishing will be enabled in the next workspace step. You can still download approved toolkit assets from the Ads Library now.</p></CardContent></Card>;
}

function SavedCreativeWorkspace({ slotId, brandName, campaignTitle }: { slotId: string; brandName: string; campaignTitle: string }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [video, setVideo] = useState<File | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [caption, setCaption] = useState(`Check out my campaign creative for ${campaignTitle} from ${brandName}.`);
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([]);
  const tooLong = duration !== null && duration > 30;
  const { data: savedCreative } = useQuery({
    queryKey: ["slot-creative", slotId],
    queryFn: () => getSlotCreative(slotId),
    retry: false,
  });
  const upload = useMutation({
    mutationFn: () => uploadSlotCreative(slotId, video!),
    onSuccess: () => {
      setVideo(null);
      setDuration(null);
      queryClient.invalidateQueries({ queryKey: ["slot-creative", slotId] });
    },
  });
  const publish = useMutation({
    mutationFn: () => publishSlotCreative(slotId, caption),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["slot-creative", slotId] });
      queryClient.invalidateQueries({ queryKey: ["social-feed"] });
      router.push("/social");
    },
  });
  const accounts = useQuery({ queryKey: ["social-accounts", "me"], queryFn: listMySocialAccounts });
  const deliveries = useQuery({
    queryKey: ["campaign-creative-deliveries", savedCreative?.native_post_id],
    queryFn: () => listCrossPosts(savedCreative!.native_post_id!),
    enabled: Boolean(savedCreative?.native_post_id),
  });
  const deliver = useMutation({
    mutationFn: () => crossPost(savedCreative!.native_post_id!, selectedAccountIds),
    onSuccess: () => {
      setSelectedAccountIds([]);
      queryClient.invalidateQueries({ queryKey: ["campaign-creative-deliveries", savedCreative?.native_post_id] });
    },
  });
  const retryDelivery = useMutation({
    mutationFn: (delivery: CrossPostDelivery) => retryCrossPost(savedCreative!.native_post_id!, delivery.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["campaign-creative-deliveries", savedCreative?.native_post_id] }),
  });
  const activeAccounts = (accounts.data ?? []).filter((account) => account.status === "active");
  const deliveredAccountIds = new Set((deliveries.data ?? []).map((delivery) => delivery.social_account_id));
  const toggleAccount = (id: string) => setSelectedAccountIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);

  return (
    <Card>
      <CardHeader><CardTitle>Create campaign ad</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">Use {brandName}&apos;s approved toolkit creative with your own footage, voice, sound, or editing style for <span className="font-medium text-foreground">{campaignTitle}</span>.</p>
        <div className="rounded-md border border-primary/30 bg-primary/5 p-3 text-sm">
          <p className="font-medium">Required before publishing</p>
          <p className="text-muted-foreground">Your finished campaign video must be 30 seconds or shorter. Clout checks its real duration again before saving.</p>
        </div>
        <div className="space-y-1">
          <Label>Upload your finished video</Label>
          <Input type="file" accept="video/mp4,video/webm,video/quicktime" onChange={(event) => {
            const file = event.target.files?.[0] ?? null;
            setVideo(file); setDuration(null);
            if (file) {
              const element = document.createElement("video");
              element.preload = "metadata";
              element.onloadedmetadata = () => { setDuration(element.duration); URL.revokeObjectURL(element.src); };
              element.src = URL.createObjectURL(file);
            }
          }} />
        </div>
        {video && <p className={tooLong ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>{video.name}{duration !== null ? ` · ${duration.toFixed(1)} seconds` : " · checking duration..."}{tooLong ? " — choose a video under 30 seconds." : ""}</p>}
        {upload.isError && <p className="text-sm text-destructive">{errorDetail(upload.error) ?? "The creative could not be saved."}</p>}
        <Button variant="outline" onClick={() => upload.mutate()} disabled={!video || tooLong || duration === null || upload.isPending}>{upload.isPending ? "Saving creative..." : savedCreative ? "Replace saved creative" : "Save draft creative"}</Button>
        {savedCreative && <div className="space-y-2 rounded-md border p-3"><p className="text-sm font-medium">Saved draft · {savedCreative.duration_seconds.toFixed(1)} seconds</p><video className="max-h-80 w-full rounded-md bg-black" controls playsInline preload="metadata"><source src={savedCreative.url} type={savedCreative.mime_type} /></video></div>}
        {savedCreative && !savedCreative.native_post_id && <div className="space-y-2 rounded-md border border-primary/30 bg-primary/5 p-3"><Label>Public Clout caption</Label><Textarea value={caption} onChange={(event) => setCaption(event.target.value)} maxLength={5000} placeholder="Tell the Clout community about this campaign..." /><Button onClick={() => publish.mutate()} disabled={!caption.trim() || publish.isPending}>{publish.isPending ? "Publishing to Clout..." : "Publish to public Clout feed"}</Button>{publish.isError && <p className="text-sm text-destructive">{errorDetail(publish.error) ?? "The creative could not be published."}</p>}</div>}
        {savedCreative?.native_post_id && <div className="rounded-md border border-green-500/30 bg-green-500/5 p-3 text-sm"><p className="font-medium">Published to the public Clout feed</p><Link href="/social" className="text-muted-foreground underline">View the public post</Link></div>}
        {savedCreative?.native_post_id && <div className="space-y-3 rounded-md border p-3"><div><p className="font-medium">Deliver to connected social accounts</p><p className="text-sm text-muted-foreground">Choose only accounts you own. Clout keeps the delivery result for each platform.</p></div>{activeAccounts.length === 0 ? <p className="text-sm text-muted-foreground">No active account is connected. <Link href="/social-accounts" className="underline">Connect an account</Link> first.</p> : <div className="space-y-2">{activeAccounts.map((account) => <label key={account.id} className="flex items-center gap-2 rounded-md border p-2 text-sm"><input type="checkbox" checked={selectedAccountIds.includes(account.id)} disabled={deliveredAccountIds.has(account.id)} onChange={() => toggleAccount(account.id)} /><span className="capitalize">{account.platform}</span><span className="text-muted-foreground">@{account.handle}</span>{deliveredAccountIds.has(account.id) && <span className="ml-auto text-xs text-muted-foreground">Already submitted</span>}</label>)}</div>}<Button onClick={() => deliver.mutate()} disabled={selectedAccountIds.length === 0 || deliver.isPending}>{deliver.isPending ? "Sending to selected accounts..." : "Deliver to selected accounts"}</Button>{deliver.isError && <p className="text-sm text-destructive">{errorDetail(deliver.error) ?? "Delivery could not be started."}</p>}{deliveries.data && deliveries.data.length > 0 && <div className="space-y-2 border-t pt-3">{deliveries.data.map((delivery) => <div key={delivery.id} className="flex flex-wrap items-center gap-2 text-sm"><span className="capitalize font-medium">{delivery.platform}</span><span className={delivery.status === "published" ? "text-green-700" : delivery.status === "failed" ? "text-destructive" : "text-muted-foreground"}>{delivery.status}</span>{delivery.post_url && <a href={delivery.post_url} target="_blank" rel="noreferrer" className="underline">View post</a>}{delivery.status === "failed" && <Button size="xs" variant="outline" onClick={() => retryDelivery.mutate(delivery)} disabled={retryDelivery.isPending}>{retryDelivery.isPending ? "Retrying..." : "Retry"}</Button>}{delivery.error_message && <span className="w-full text-xs text-muted-foreground">{delivery.error_message}</span>}</div>)}</div>}</div>}
        <p className="text-xs text-muted-foreground">Publishing here makes the ad visible to everyone on Clout. External delivery only occurs after the owner selects a connected account.</p>
      </CardContent>
    </Card>
  );
}

function SlotDetail({ slotId }: { slotId: string }) {
  const router = useRouter();

  const { data: slots } = useQuery({ queryKey: ["slots", "mine"], queryFn: listMySlots });
  const slot = slots?.find((s) => s.id === slotId);

  const { data: post, isLoading: postLoading } = useQuery({
    queryKey: ["slot-post", slotId],
    queryFn: () => getSlotPost(slotId),
    retry: false,
  });

  if (!slot) return <p className="text-sm text-muted-foreground">Loading slot...</p>;

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.push("/influencer/slots")}>
        ← Back to my slots
      </Button>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{slot.advertisement_title}</CardTitle>
          <div className="flex items-center gap-1">
            {slot.recovery_generation > 0 && (
              <Badge variant="outline" title="This slot was recycled from an earlier delivery shortfall">
                Recovered
              </Badge>
            )}
            <Badge className="capitalize">{slot.status}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p className="capitalize">
            {slot.brand_name} · {slot.platform} · {slot.tier} tier
          </p>
          <p>{slot.target_views.toLocaleString()} views target</p>
          {slot.delivered_pct !== null && <p>Delivered: {Number(slot.delivered_pct).toFixed(0)}%</p>}
          <Button size="xs" variant="outline" render={<Link href={`/messages?with=${slot.brand_id}`} />}>
            Message brand
          </Button>
        </CardContent>
      </Card>

      {slot.status === "claimed" && <SavedCreativeWorkspace slotId={slotId} brandName={slot.brand_name} campaignTitle={slot.advertisement_title} />}

      <Card>
        <CardHeader>
          <CardTitle>Post</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {postLoading && <p className="text-sm text-muted-foreground">Loading...</p>}

          {!postLoading && !post && slot.status === "claimed" && (
            <CreatePostForm slotId={slotId} platform={slot.platform} />
          )}

          {post && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm">
                <Badge variant={postStatusVariant(post.status)} className="capitalize">
                  {post.status}
                </Badge>
                <span className="text-muted-foreground capitalize">{post.publish_mode} mode</span>
              </div>

              {post.post_url && (
                <a href={post.post_url} target="_blank" rel="noreferrer" className="text-sm underline">
                  View live post
                </a>
              )}

              {post.publish_mode === "manual" && post.status === "pending" && <ManualSubmitForm slotId={slotId} />}

              {post.status === "published" && (
                <div>
                  <h3 className="mb-2 text-sm font-medium text-muted-foreground">Performance</h3>
                  <MetricsPanel slotId={slotId} />
                </div>
              )}

              {post.status === "published" && (
                <div>
                  <h3 className="mb-2 text-sm font-medium text-muted-foreground">Comments</h3>
                  <CommentsPanel slotId={slotId} />
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function SlotDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <RequireUserType allow={["influencer"]}>
      <DashboardShell title="Slot detail">
        <SlotDetail slotId={params.id} />
      </DashboardShell>
    </RequireUserType>
  );
}
