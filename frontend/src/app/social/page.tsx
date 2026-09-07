"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bookmark,
  Compass,
  Flag,
  Heart,
  ImagePlus,
  MessageCircle,
  Repeat2,
  Send,
  Share2,
  Sparkles,
  UserRoundPlus,
  UserX,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  addPostComment,
  blockUser,
  crossPost,
  createPost,
  listFeed,
  listForYouFeed,
  listCrossPosts,
  listPostComments,
  repostPost,
  reportPost,
  retryCrossPost,
  togglePostLike,
  togglePostSave,
  uploadPostMedia,
  type PostVisibility,
  type SocialPost,
} from "@/lib/social-feed-api";
import { listMySocialAccounts } from "@/lib/social-api";
import { useAuthStore } from "@/store/auth-store";

function initials(name: string) {
  return name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function relativeDate(value?: string) {
  if (!value) return "Recently";
  const elapsed = Date.now() - new Date(value).getTime();
  if (!Number.isFinite(elapsed) || elapsed < 60_000) return "Just now";
  if (elapsed < 3_600_000) return `${Math.floor(elapsed / 60_000)}m`;
  if (elapsed < 86_400_000) return `${Math.floor(elapsed / 3_600_000)}h`;
  return `${Math.floor(elapsed / 86_400_000)}d`;
}

function PostMedia({ media }: { media: SocialPost["media"][number] }) {
  if (media.media_type === "image") {
    return (
      <img
        src={media.url}
        alt="Post media"
        className="max-h-[38rem] w-full rounded-xl border bg-muted object-cover"
      />
    );
  }
  if (media.media_type === "video") {
    return (
      <div className="overflow-hidden rounded-xl border bg-black">
        <video
          src={media.url}
          controls
          playsInline
          preload="metadata"
          className="max-h-[38rem] w-full"
        />
      </div>
    );
  }
  return (
    <div className="rounded-xl border bg-muted/30 p-3">
      <audio src={media.url} controls preload="metadata" className="w-full" />
    </div>
  );
}

function ConnectedAccountShare({ post }: { post: SocialPost }) {
  const user = useAuthStore((state) => state.user);
  const [open, setOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const isOwner = user?.id === post.author.id;
  const hasReadyVideo = post.media.some(
    (media) =>
      media.media_type === "video" && media.processing_status === "ready",
  );
  const accounts = useQuery({
    queryKey: ["social-accounts", "me"],
    queryFn: listMySocialAccounts,
    enabled: isOwner && open,
  });
  const deliveries = useQuery({
    queryKey: ["cross-posts", post.id],
    queryFn: () => listCrossPosts(post.id),
    enabled: isOwner && open,
  });
  const publish = useMutation({
    mutationFn: () => crossPost(post.id, selectedIds),
    onSuccess: () => {
      setSelectedIds([]);
      deliveries.refetch();
    },
  });
  const retry = useMutation({
    mutationFn: (distributionId: string) =>
      retryCrossPost(post.id, distributionId),
    onSuccess: () => deliveries.refetch(),
  });

  if (!isOwner || !hasReadyVideo) return null;
  const activeAccounts = (accounts.data ?? []).filter(
    (account) => account.status === "active",
  );
  return (
    <section className="space-y-3 rounded-xl border border-primary/15 bg-primary/5 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold">
            Share to your connected accounts
          </p>
          <p className="text-xs text-muted-foreground">
            Choose only accounts you own. CLOUT records each delivery
            separately.
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setOpen((value) => !value)}
        >
          <Share2 className="size-4" />
          {open ? "Close" : "Share"}
        </Button>
      </div>
      {open && (
        <div className="space-y-3 border-t pt-3">
          {accounts.isLoading && (
            <p className="text-xs text-muted-foreground">
              Loading connected accounts...
            </p>
          )}
          {!accounts.isLoading && activeAccounts.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Connect an account first in{" "}
              <Link
                href="/social-accounts"
                className="font-medium text-primary hover:underline"
              >
                Connected accounts
              </Link>
              .
            </p>
          )}
          {activeAccounts.length > 0 && (
            <>
              <div className="grid gap-2 sm:grid-cols-2">
                {activeAccounts.map((account) => (
                  <label
                    key={account.id}
                    className="flex cursor-pointer items-center gap-2 rounded-lg border bg-background p-2 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(account.id)}
                      onChange={() =>
                        setSelectedIds((current) =>
                          current.includes(account.id)
                            ? current.filter((id) => id !== account.id)
                            : [...current, account.id],
                        )
                      }
                    />
                    <span className="capitalize">{account.platform}</span>
                    <span className="truncate text-muted-foreground">
                      @{account.handle}
                    </span>
                  </label>
                ))}
              </div>
              <Button
                size="sm"
                disabled={selectedIds.length === 0 || publish.isPending}
                onClick={() => publish.mutate()}
              >
                {publish.isPending ? "Sending..." : "Send to selected accounts"}
              </Button>
            </>
          )}
          {publish.isError && (
            <p className="text-xs text-destructive">
              Could not start delivery. Check your connection and try again.
            </p>
          )}
          {deliveries.data && deliveries.data.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                Delivery status
              </p>
              {deliveries.data.map((delivery) => (
                <div
                  key={delivery.id}
                  className="flex flex-wrap items-center gap-2 rounded-lg border bg-background p-2 text-xs"
                >
                  <Badge
                    variant={
                      delivery.status === "published"
                        ? "success"
                        : delivery.status === "failed"
                          ? "destructive"
                          : "secondary"
                    }
                    className="capitalize"
                  >
                    {delivery.platform}: {delivery.status}
                  </Badge>
                  {delivery.post_url && (
                    <a
                      className="font-medium text-primary hover:underline"
                      href={delivery.post_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open post
                    </a>
                  )}
                  {delivery.error_message && (
                    <span className="flex-1 text-muted-foreground">
                      {delivery.error_message}
                    </span>
                  )}
                  {delivery.status === "failed" && (
                    <Button
                      size="xs"
                      variant="outline"
                      disabled={retry.isPending}
                      onClick={() => retry.mutate(delivery.id)}
                    >
                      {retry.isPending ? "Retrying..." : "Retry"}
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function PostCard({ post }: { post: SocialPost }) {
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const [commentsOpen, setCommentsOpen] = useState(false);
  const comments = useQuery({
    queryKey: ["social-comments", post.id],
    queryFn: () => listPostComments(post.id),
    enabled: commentsOpen,
  });
  const refreshFeed = () =>
    queryClient.invalidateQueries({ queryKey: ["social-feed"] });
  const addComment = useMutation({
    mutationFn: () => addPostComment(post.id, comment),
    onSuccess: () => {
      setComment("");
      queryClient.invalidateQueries({ queryKey: ["social-comments", post.id] });
      refreshFeed();
    },
  });
  const repost = useMutation({
    mutationFn: () => repostPost(post.id),
    onSuccess: refreshFeed,
  });
  async function shareExternally() {
    if (navigator.share)
      await navigator.share({
        title: `${post.author.name} on CLOUT`,
        text: post.body,
      });
  }

  return (
    <article className="overflow-hidden rounded-2xl border bg-card/90 shadow-sm backdrop-blur-sm">
      <div className="space-y-4 p-4 sm:p-5">
        <header className="flex items-center justify-between gap-3">
          <Link
            href={`/social/profiles/${post.author.id}`}
            className="flex min-w-0 items-center gap-3"
          >
            <Avatar size="lg">
              <AvatarImage src={post.author.picture_url ?? undefined} />
              <AvatarFallback>{initials(post.author.name)}</AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="truncate font-semibold hover:underline">
                {post.author.name}
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {post.author.username ? `@${post.author.username} · ` : ""}
                {relativeDate(post.created_at)}
              </p>
            </div>
          </Link>
          {post.visibility !== "public" && (
            <Badge variant="outline" className="capitalize">
              {post.visibility.replace("_", " ")}
            </Badge>
          )}
        </header>
        <p className="whitespace-pre-wrap text-[15px] leading-6">{post.body}</p>
        {post.hashtags && post.hashtags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {post.hashtags.map((tag) => (
              <Link
                href={`/social/discover?hashtag=${encodeURIComponent(tag)}`}
                key={tag}
              >
                <Badge variant="secondary">#{tag}</Badge>
              </Link>
            ))}
          </div>
        )}
        {post.media.map((media) => (
          <div key={media.id} className="space-y-1">
            <PostMedia media={media} />
            {media.processing_status !== "ready" && (
              <p className="text-xs text-muted-foreground">
                Preparing the optimized version — the verified upload is
                playable now.
              </p>
            )}
          </div>
        ))}
        <div className="flex flex-wrap items-center gap-1 border-t pt-3">
          <Button
            size="sm"
            variant="ghost"
            className={
              post.liked_by_me ? "text-rose-600 hover:text-rose-600" : ""
            }
            onClick={() => togglePostLike(post.id).then(refreshFeed)}
          >
            <Heart
              className={post.liked_by_me ? "size-4 fill-current" : "size-4"}
            />{" "}
            {post.like_count || "Like"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setCommentsOpen((open) => !open)}
          >
            <MessageCircle className="size-4" />{" "}
            {post.comment_count || "Comment"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => repost.mutate()}
            disabled={repost.isPending}
          >
            <Repeat2 className="size-4" />{" "}
            {repost.isPending ? "Reposting" : "Repost"}
          </Button>
          {typeof navigator !== "undefined" && "share" in navigator && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => void shareExternally()}
            >
              <Share2 className="size-4" /> Share
            </Button>
          )}
          <Button
            size="icon-sm"
            variant="ghost"
            className="ml-auto"
            onClick={() => togglePostSave(post.id).then(refreshFeed)}
            aria-label="Save post"
          >
            <Bookmark
              className={post.saved_by_me ? "size-4 fill-current" : "size-4"}
            />
          </Button>
        </div>
        <ConnectedAccountShare post={post} />
        {commentsOpen && (
          <section className="space-y-3 border-t pt-3">
            {comments.data?.map((item) => (
              <div
                key={item.id}
                className="rounded-lg bg-muted/55 px-3 py-2 text-sm"
              >
                <b>{item.author.name}</b>
                <span className="ml-1">{item.body}</span>
              </div>
            ))}
            <div className="flex items-end gap-2">
              <Textarea
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                placeholder="Add a comment…"
                className="min-h-10 resize-none"
              />
              <Button
                size="icon"
                aria-label="Send comment"
                disabled={!comment.trim() || addComment.isPending}
                onClick={() => addComment.mutate()}
              >
                <Send className="size-4" />
              </Button>
            </div>
          </section>
        )}
      </div>
    </article>
  );
}

function SafetyActions({ post }: { post: SocialPost }) {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("spam");
  const report = useMutation({
    mutationFn: () => reportPost(post.id, reason),
    onSuccess: () => setOpen(false),
  });
  const block = useMutation({
    mutationFn: () => blockUser(post.author.id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["social-feed"] }),
  });
  if (user?.id === post.author.id) return null;
  return (
    <div className="flex flex-wrap items-center gap-1 px-2">
      <Button
        size="xs"
        variant="ghost"
        className="text-muted-foreground"
        onClick={() => setOpen((value) => !value)}
      >
        <Flag className="size-3.5" /> Report
      </Button>
      <Button
        size="xs"
        variant="ghost"
        className="text-muted-foreground"
        onClick={() => block.mutate()}
        disabled={block.isPending}
      >
        <UserX className="size-3.5" />{" "}
        {block.isPending ? "Blocking…" : "Block creator"}
      </Button>
      {open && (
        <div className="flex w-full flex-wrap items-center gap-2 rounded-lg border bg-card p-2">
          <select
            aria-label="Report reason"
            className="h-8 rounded-md border bg-background px-2 text-sm"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          >
            <option value="spam">Spam or scam</option>
            <option value="harassment">Harassment</option>
            <option value="hate">Hate or abuse</option>
            <option value="misinformation">Misleading content</option>
            <option value="other">Other</option>
          </select>
          <Button
            size="xs"
            variant="destructive"
            onClick={() => report.mutate()}
            disabled={report.isPending}
          >
            {report.isPending ? "Sending…" : "Submit report"}
          </Button>
        </div>
      )}
      {(report.isError || block.isError) && (
        <p className="w-full text-xs text-destructive">
          This safety action could not be completed. Please try again.
        </p>
      )}
    </div>
  );
}

function Composer() {
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [visibility, setVisibility] = useState<PostVisibility>("public");
  const publish = useMutation({
    mutationFn: async () => {
      const post = await createPost(body, visibility);
      if (file) await uploadPostMedia(post.id, file);
    },
    onSuccess: () => {
      setBody("");
      setFile(null);
      queryClient.invalidateQueries({ queryKey: ["social-feed"] });
    },
  });
  return (
    <Card className="overflow-hidden border-primary/15 bg-card/95 shadow-sm">
      <CardContent className="space-y-3 p-4 sm:p-5">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-primary" />
          <p className="text-sm font-semibold">Create a post</p>
          <Badge variant="secondary" className="ml-auto">
            Build your audience
          </Badge>
        </div>
        <Textarea
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder="What do you want to share with the CLOUT community?"
          className="min-h-24 resize-none border-0 bg-muted/45 shadow-none focus-visible:ring-1"
        />
        <div className="flex flex-wrap items-center gap-2">
          <label className="inline-flex h-9 cursor-pointer items-center gap-2 rounded-md border bg-background px-3 text-sm font-medium transition-colors hover:bg-muted">
            <ImagePlus className="size-4 text-primary" />
            {file ? file.name : "Photo, video or audio"}
            <input
              className="sr-only"
              type="file"
              accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime,audio/mpeg,audio/wav,audio/mp4,audio/aac"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <select
            aria-label="Post visibility"
            className="h-9 rounded-md border bg-background px-3 text-sm"
            value={visibility}
            onChange={(event) =>
              setVisibility(event.target.value as PostVisibility)
            }
          >
            <option value="public">Public</option>
            <option value="followers">Followers only</option>
            <option value="brands_only">Brands only</option>
            <option value="private">Only me</option>
          </select>
          <Button
            className="ml-auto"
            disabled={!body.trim() || publish.isPending}
            onClick={() => publish.mutate()}
          >
            {publish.isPending ? "Publishing…" : "Publish"}
          </Button>
        </div>
        {publish.isError && (
          <p className="text-sm text-destructive">
            Your post could not be published. Please try again.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function CommunitySidebar() {
  return (
    <aside className="hidden space-y-4 lg:block">
      <Card className="bg-card/85 backdrop-blur-sm">
        <CardContent className="space-y-3 p-4">
          <div className="flex items-center gap-2">
            <Compass className="size-4 text-primary" />
            <p className="font-semibold">Find your community</p>
          </div>
          <p className="text-sm text-muted-foreground">
            Follow creators, discover campaign ideas, and join conversations
            that fit your audience.
          </p>
          <Button
            className="w-full"
            variant="outline"
            render={<Link href="/social/discover" />}
          >
            <UserRoundPlus className="size-4" /> Discover creators
          </Button>
        </CardContent>
      </Card>
      <Card className="bg-card/85 backdrop-blur-sm">
        <CardContent className="space-y-3 p-4">
          <p className="font-semibold">How CLOUT works</p>
          <ol className="space-y-3 text-sm text-muted-foreground">
            <li>
              <b className="mr-2 text-foreground">1</b>Brands share approved
              creative with eligible creators.
            </li>
            <li>
              <b className="mr-2 text-foreground">2</b>Creators produce
              authentic campaign content.
            </li>
            <li>
              <b className="mr-2 text-foreground">3</b>Public posts reach the
              CLOUT community.
            </li>
          </ol>
        </CardContent>
      </Card>
      <p className="px-2 text-xs text-muted-foreground">
        Keep CLOUT welcoming: report harmful posts and block unwanted accounts.
      </p>
    </aside>
  );
}

export default function SocialPage() {
  const [mode, setMode] = useState<"for-you" | "following">("for-you");
  const feed = useQuery({
    queryKey: ["social-feed", mode],
    queryFn: () => (mode === "for-you" ? listForYouFeed() : listFeed()),
    refetchInterval: (query) =>
      query.state.data?.some((post) =>
        post.media.some(
          (media) =>
            media.processing_status === "pending" ||
            media.processing_status === "processing",
        ),
      )
        ? 2500
        : false,
  });
  return (
    <RequireUserType allow={["brand", "influencer"]}>
      <DashboardShell title="Clout feed">
        <main className="mx-auto grid w-full max-w-6xl gap-7 lg:grid-cols-[minmax(0,1fr)_19rem]">
          <section className="min-w-0 space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-primary">CLOUT SOCIAL</p>
                <h1 className="text-2xl font-bold tracking-tight">
                  Your community, in one feed
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  Watch, react, share, and discover work from creators you
                  trust.
                </p>
              </div>
              <Button
                variant="outline"
                className="lg:hidden"
                render={<Link href="/social/discover" />}
              >
                <Compass className="size-4" /> Discover
              </Button>
            </div>
            <Composer />
            <nav
              aria-label="Feed filter"
              className="flex gap-1 rounded-xl border bg-card/75 p-1"
            >
              <Button
                size="sm"
                className="flex-1"
                variant={mode === "for-you" ? "default" : "ghost"}
                onClick={() => setMode("for-you")}
              >
                For you
              </Button>
              <Button
                size="sm"
                className="flex-1"
                variant={mode === "following" ? "default" : "ghost"}
                onClick={() => setMode("following")}
              >
                Following
              </Button>
            </nav>
            {feed.isLoading && (
              <div className="rounded-xl border bg-card p-8 text-center text-sm text-muted-foreground">
                Building your personalised feed…
              </div>
            )}
            {!feed.isLoading && feed.data?.length === 0 && (
              <div className="rounded-xl border border-dashed bg-card/70 p-8 text-center">
                <Sparkles className="mx-auto mb-3 size-6 text-primary" />
                <p className="font-medium">
                  Your feed is ready for its first story
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Follow creators or publish a public post to start your
                  community.
                </p>
                <Button
                  className="mt-4"
                  variant="outline"
                  render={<Link href="/social/discover" />}
                >
                  Discover creators
                </Button>
              </div>
            )}
            {feed.data?.map((post) => (
              <div key={post.id} className="space-y-1">
                <PostCard post={post} />
                <SafetyActions post={post} />
              </div>
            ))}
          </section>
          <CommunitySidebar />
        </main>
      </DashboardShell>
    </RequireUserType>
  );
}
