"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getSocialProfile, toggleFollow } from "@/lib/social-feed-api";

export default function SocialProfilePage() {
  const { id } = useParams<{ id: string }>(); const qc = useQueryClient();
  const profile = useQuery({ queryKey: ["social-profile", id], queryFn: () => getSocialProfile(id) });
  const follow = useMutation({ mutationFn: () => toggleFollow(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["social-profile", id] }) });
  return <RequireUserType allow={["brand", "influencer"]}><DashboardShell title="Creator profile"><div className="mx-auto max-w-2xl space-y-4">{profile.isLoading ? <p className="text-sm text-muted-foreground">Loading profile...</p> : profile.data ? <><Card><CardContent className="flex items-center justify-between pt-6"><div><h1 className="font-semibold">{profile.data.author.name}</h1>{profile.data.author.username && <p className="text-sm text-muted-foreground">@{profile.data.author.username}</p>}<p className="mt-2 text-xs text-muted-foreground">{profile.data.follower_count} followers · {profile.data.following_count} following</p></div><Button onClick={() => follow.mutate()} disabled={follow.isPending}>{profile.data.following_by_me ? "Following" : "Follow"}</Button></CardContent></Card>{profile.data.posts.map(post => <Card key={post.id}><CardContent className="space-y-2 pt-6"><p className="whitespace-pre-wrap text-sm">{post.body}</p>{post.media.map(media => media.media_type === "image" ? <img key={media.id} src={media.url} alt="Post media" className="max-h-96 w-full rounded-lg object-cover" /> : null)}</CardContent></Card>)}</> : <p className="text-sm text-destructive">Profile could not be loaded.</p>}</div></DashboardShell></RequireUserType>;
}
