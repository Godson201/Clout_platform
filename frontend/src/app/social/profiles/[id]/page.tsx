"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getSocialProfile, listProfileFollowers, listProfileFollowing, repostPost, toggleFollow } from "@/lib/social-feed-api";
import { useAuthStore } from "@/store/auth-store";

type Person = { id: string; name: string; username?: string | null };

function PeopleList({ title, people }: { title: string; people: Person[] }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold">{title}</h2>
      {people.length === 0 ? <p className="text-sm text-muted-foreground">No one to show yet.</p> : people.map((person) => (
        <div key={person.id} className="flex items-center justify-between gap-3 rounded-xl border bg-card/80 p-3">
          <Link href={`/social/profiles/${person.id}`} className="min-w-0 hover:underline"><p className="truncate text-sm font-medium">{person.name}</p>{person.username && <p className="truncate text-xs text-muted-foreground">@{person.username}</p>}</Link>
          <Button size="sm" variant="outline" render={<Link href={`/messages?with=${person.id}`}>Chat</Link>} />
        </div>
      ))}
    </section>
  );
}

export default function SocialProfilePage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((state) => state.user);
  const [peopleView, setPeopleView] = useState<"followers" | "following" | null>(null);
  const profile = useQuery({ queryKey: ["social-profile", id], queryFn: () => getSocialProfile(id) });
  const followers = useQuery({ queryKey: ["social-profile-followers", id], queryFn: () => listProfileFollowers(id), enabled: peopleView === "followers" });
  const following = useQuery({ queryKey: ["social-profile-following", id], queryFn: () => listProfileFollowing(id), enabled: peopleView === "following" });
  const follow = useMutation({ mutationFn: () => toggleFollow(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["social-profile", id] }) });
  const repost = useMutation({ mutationFn: (postId: string) => repostPost(postId), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["social-feed"] }) });
  const ownProfile = currentUser?.id === id;

  return (
    <RequireUserType allow={["brand", "influencer"]}>
      <DashboardShell title="Creator profile">
        <div className="mx-auto max-w-2xl space-y-4">
          {profile.isLoading ? <p className="text-sm text-muted-foreground">Loading profile...</p> : profile.data ? <>
            <Card><CardContent className="space-y-4 pt-6"><div className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="font-semibold">{profile.data.author.name}</h1>{profile.data.author.username && <p className="text-sm text-muted-foreground">@{profile.data.author.username}</p>}</div>{!ownProfile && <div className="flex gap-2"><Button variant="outline" render={<Link href={`/messages?with=${id}`}>Chat</Link>} /><Button onClick={() => follow.mutate()} disabled={follow.isPending}>{follow.isPending ? "Saving..." : profile.data.following_by_me ? "Following" : "Follow"}</Button></div>}</div><div className="flex gap-4 text-sm"><button className="hover:underline" onClick={() => setPeopleView(peopleView === "followers" ? null : "followers")}><b>{profile.data.follower_count}</b> followers</button><button className="hover:underline" onClick={() => setPeopleView(peopleView === "following" ? null : "following")}><b>{profile.data.following_count}</b> following</button></div></CardContent></Card>
            {peopleView === "followers" && <PeopleList title="Followers" people={followers.data?.items ?? []} />}
            {peopleView === "following" && <PeopleList title="Following" people={following.data?.items ?? []} />}
            {profile.data.posts.map((post) => <Card key={post.id}><CardContent className="space-y-3 pt-6"><p className="whitespace-pre-wrap text-sm">{post.body}</p>{post.media.map((media) => media.media_type === "image" ? <img key={media.id} src={media.url} alt="Post media" className="max-h-96 w-full rounded-lg object-cover" /> : media.media_type === "video" ? <video key={media.id} controls className="max-h-96 w-full rounded-lg bg-black" src={media.url} /> : null)}<div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => repost.mutate(post.id)} disabled={repost.isPending}>{repost.isPending ? "Sharing..." : "Share to my followers"}</Button>{!ownProfile && <Button size="sm" variant="ghost" render={<Link href={`/messages?with=${id}`}>Chat creator</Link>} />}</div></CardContent></Card>)}
          </> : <p className="text-sm text-destructive">Profile could not be loaded.</p>}
        </div>
      </DashboardShell>
    </RequireUserType>
  );
}
