"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Heart, MessageCircle, Bookmark } from "lucide-react";
import { useState } from "react";
import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { addPostComment, createPost, listFeed, listPostComments, togglePostLike, togglePostSave, uploadPostMedia, type SocialPost } from "@/lib/social-feed-api";

function PostCard({ post }: { post: SocialPost }) {
  const qc = useQueryClient(); const [comment, setComment] = useState(""); const [open, setOpen] = useState(false);
  const comments = useQuery({ queryKey: ["social-comments", post.id], queryFn: () => listPostComments(post.id), enabled: open });
  const refresh = () => qc.invalidateQueries({ queryKey: ["social-feed"] });
  const add = useMutation({ mutationFn: () => addPostComment(post.id, comment), onSuccess: () => { setComment(""); refresh(); qc.invalidateQueries({ queryKey: ["social-comments", post.id] }); } });
  return <Card><CardContent className="space-y-3 pt-6"><div><p className="font-medium">{post.author.name}</p>{post.author.username && <p className="text-xs text-muted-foreground">@{post.author.username}</p>}</div><p className="whitespace-pre-wrap text-sm">{post.body}</p>{post.media.map(media => media.media_type === "image" ? <img key={media.id} src={media.url} alt="Post media" className="max-h-96 w-full rounded-lg object-cover" /> : media.media_type === "video" ? <video key={media.id} src={media.url} controls className="max-h-96 w-full rounded-lg" /> : <audio key={media.id} src={media.url} controls className="w-full" />)}<div className="flex gap-2"><Button size="sm" variant={post.liked_by_me ? "default" : "outline"} onClick={() => togglePostLike(post.id).then(refresh)}><Heart className="size-4" /> {post.like_count}</Button><Button size="sm" variant="outline" onClick={() => setOpen(!open)}><MessageCircle className="size-4" /> {post.comment_count}</Button><Button size="sm" variant={post.saved_by_me ? "default" : "outline"} onClick={() => togglePostSave(post.id).then(refresh)}><Bookmark className="size-4" /></Button></div>{open && <div className="space-y-2 border-t pt-3">{comments.data?.map(c => <p key={c.id} className="text-sm"><span className="font-medium">{c.author.name}: </span>{c.body}</p>)}<div className="flex gap-2"><Textarea value={comment} onChange={e => setComment(e.target.value)} placeholder="Write a comment" className="min-h-10" /><Button disabled={!comment.trim() || add.isPending} onClick={() => add.mutate()}>Reply</Button></div></div>}</CardContent></Card>;
}

export default function SocialPage() {
  const qc = useQueryClient(); const [body, setBody] = useState(""); const [file, setFile] = useState<File | null>(null); const feed = useQuery({ queryKey: ["social-feed"], queryFn: listFeed });
  const publish = useMutation({ mutationFn: async () => { const post = await createPost(body); if (file) await uploadPostMedia(post.id, file); }, onSuccess: () => { setBody(""); setFile(null); qc.invalidateQueries({ queryKey: ["social-feed"] }); } });
  return <RequireUserType allow={["brand", "influencer"]}><DashboardShell title="Clout feed"><div className="mx-auto max-w-2xl space-y-4"><Card><CardContent className="space-y-3 pt-6"><Textarea value={body} onChange={e => setBody(e.target.value)} placeholder="Share something with the Clout community..." /><input type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime,audio/mpeg,audio/wav,audio/mp4,audio/aac" onChange={e => setFile(e.target.files?.[0] ?? null)} />{file && <p className="text-xs text-muted-foreground">{file.name}</p>}<div className="flex justify-end"><Button disabled={!body.trim() || publish.isPending} onClick={() => publish.mutate()}>Publish</Button></div></CardContent></Card>{feed.isLoading && <p className="text-sm text-muted-foreground">Loading feed...</p>}{feed.data?.length === 0 && <p className="text-sm text-muted-foreground">Follow creators and brands to personalise your feed.</p>}{feed.data?.map(post => <PostCard key={post.id} post={post} />)}</div></DashboardShell></RequireUserType>;
}
