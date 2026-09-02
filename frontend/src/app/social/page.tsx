"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bookmark, Flag, Heart, MessageCircle, Repeat2, Share2, UserX } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { addPostComment, blockUser, createPost, listFeed, listForYouFeed, listPostComments, repostPost, reportPost, togglePostLike, togglePostSave, uploadPostMedia, type PostVisibility, type SocialPost } from "@/lib/social-feed-api";
import { useAuthStore } from "@/store/auth-store";

function PostMedia({ media }: { media: SocialPost["media"][number] }) {
  return <div>{media.media_type === "image" ? <img src={media.url} alt="Post media" className="max-h-96 w-full rounded-lg object-cover" /> : media.media_type === "video" ? <video src={media.url} controls playsInline preload="metadata" className="max-h-96 w-full rounded-lg bg-black" /> : <audio src={media.url} controls preload="metadata" className="w-full" />}{media.processing_status !== "ready" && <p className="mt-1 text-xs text-muted-foreground">Video is processing. You can still play the verified upload while CLOUT prepares it.</p>}</div>;
}

function PostCard({ post }: { post: SocialPost }) {
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const [commentsOpen, setCommentsOpen] = useState(false);
  const comments = useQuery({ queryKey: ["social-comments", post.id], queryFn: () => listPostComments(post.id), enabled: commentsOpen });
  const refreshFeed = () => queryClient.invalidateQueries({ queryKey: ["social-feed"] });
  const addComment = useMutation({ mutationFn: () => addPostComment(post.id, comment), onSuccess: () => { setComment(""); queryClient.invalidateQueries({ queryKey: ["social-comments", post.id] }); refreshFeed(); } });
  const repost = useMutation({ mutationFn: () => repostPost(post.id), onSuccess: refreshFeed });
  async function shareExternally() { if (navigator.share) await navigator.share({ title: `${post.author.name} on CLOUT`, text: post.body }); }
  return <Card><CardContent className="space-y-3 pt-6"><header><Link href={`/social/profiles/${post.author.id}`} className="inline-block hover:underline"><p className="font-medium">{post.author.name}</p>{post.author.username && <p className="text-xs text-muted-foreground">@{post.author.username}</p>}</Link></header><p className="whitespace-pre-wrap text-sm">{post.body}</p>{post.media.map((media) => <PostMedia key={media.id} media={media} />)}<div className="flex flex-wrap gap-2"><Button size="sm" variant={post.liked_by_me ? "default" : "outline"} onClick={() => togglePostLike(post.id).then(refreshFeed)}><Heart className="size-4" /> {post.like_count}</Button><Button size="sm" variant="outline" onClick={() => setCommentsOpen((open) => !open)}><MessageCircle className="size-4" /> {post.comment_count}</Button><Button size="sm" variant="outline" onClick={() => repost.mutate()} disabled={repost.isPending}><Repeat2 className="size-4" /> {repost.isPending ? "Reposting..." : "Repost"}</Button>{typeof navigator !== "undefined" && "share" in navigator && <Button size="sm" variant="ghost" onClick={() => void shareExternally()}><Share2 className="size-4" /> Share</Button>}<Button size="sm" variant={post.saved_by_me ? "default" : "outline"} onClick={() => togglePostSave(post.id).then(refreshFeed)} aria-label="Save post"><Bookmark className="size-4" /></Button></div>{commentsOpen && <section className="space-y-2 border-t pt-3">{comments.data?.map((item) => <p key={item.id} className="text-sm"><b>{item.author.name}: </b>{item.body}</p>)}<div className="flex gap-2"><Textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Write a comment" className="min-h-10" /><Button disabled={!comment.trim() || addComment.isPending} onClick={() => addComment.mutate()}>Reply</Button></div></section>}</CardContent></Card>;
}

function SafetyActions({ post }: { post: SocialPost }) {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("spam");
  const isOwnPost = user?.id === post.author.id;
  const report = useMutation({ mutationFn: () => reportPost(post.id, reason), onSuccess: () => setOpen(false) });
  const block = useMutation({ mutationFn: () => blockUser(post.author.id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["social-feed"] }) });
  if (isOwnPost) return null;
  return <Card className="-mt-3"><CardContent className="space-y-2 py-3"><div className="flex flex-wrap gap-2"><Button size="xs" variant="ghost" onClick={() => setOpen((value) => !value)}><Flag className="size-3.5" /> Report</Button><Button size="xs" variant="ghost" onClick={() => block.mutate()} disabled={block.isPending}><UserX className="size-3.5" /> {block.isPending ? "Blocking..." : "Block creator"}</Button></div>{open && <div className="flex flex-wrap items-center gap-2 rounded-md border p-2"><select className="h-8 rounded-md border bg-background px-2 text-sm" value={reason} onChange={(event) => setReason(event.target.value)}><option value="spam">Spam or scam</option><option value="harassment">Harassment</option><option value="hate">Hate or abuse</option><option value="misinformation">Misleading content</option><option value="other">Other</option></select><Button size="xs" variant="destructive" onClick={() => report.mutate()} disabled={report.isPending}>{report.isPending ? "Sending..." : "Submit report"}</Button></div>}{(report.isError || block.isError) && <p className="text-xs text-destructive">This safety action could not be completed. Please try again.</p>}</CardContent></Card>;
}

function Composer() {
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [visibility, setVisibility] = useState<PostVisibility>("public");
  const publish = useMutation({ mutationFn: async () => { const post = await createPost(body, visibility); if (file) await uploadPostMedia(post.id, file); }, onSuccess: () => { setBody(""); setFile(null); queryClient.invalidateQueries({ queryKey: ["social-feed"] }); } });
  return <Card><CardContent className="space-y-3 pt-6"><Textarea value={body} onChange={(event) => setBody(event.target.value)} placeholder="Share something with the Clout community..." /><select className="h-9 rounded-md border bg-background px-3 text-sm" value={visibility} onChange={(event) => setVisibility(event.target.value as PostVisibility)}><option value="public">Public — everyone on CLOUT</option><option value="followers">Followers only</option><option value="brands_only">Brands only</option><option value="private">Only me</option></select><input type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime,audio/mpeg,audio/wav,audio/mp4,audio/aac" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /><Button disabled={!body.trim() || publish.isPending} onClick={() => publish.mutate()}>{publish.isPending ? "Publishing..." : "Publish"}</Button>{publish.isError && <p className="text-sm text-destructive">Your post could not be published. Please try again.</p>}</CardContent></Card>;
}

export default function SocialPage() {
  const [mode, setMode] = useState<"for-you" | "following">("for-you");
  const feed = useQuery({ queryKey: ["social-feed", mode], queryFn: () => mode === "for-you" ? listForYouFeed() : listFeed(), refetchInterval: (query) => query.state.data?.some((post) => post.media.some((media) => media.processing_status === "pending" || media.processing_status === "processing")) ? 2500 : false });
  return <RequireUserType allow={["brand", "influencer"]}><DashboardShell title="Clout feed"><main className="mx-auto max-w-2xl space-y-4"><Composer /><div className="flex gap-2 border-b"><Button size="sm" variant={mode === "for-you" ? "default" : "ghost"} onClick={() => setMode("for-you")}>For you</Button><Button size="sm" variant={mode === "following" ? "default" : "ghost"} onClick={() => setMode("following")}>Following</Button><Button size="sm" variant="ghost" render={<Link href="/social/discover" />}>Discover creators</Button></div>{feed.isLoading && <p className="text-sm text-muted-foreground">Building your feed...</p>}{!feed.isLoading && feed.data?.length === 0 && <p className="text-sm text-muted-foreground">Follow people or explore new posts to personalise this feed.</p>}{feed.data?.map((post) => <div key={post.id} className="space-y-1"><PostCard post={post} /><SafetyActions post={post} /></div>)}</main></DashboardShell></RequireUserType>;
}
