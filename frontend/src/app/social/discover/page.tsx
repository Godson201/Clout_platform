"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { listCreators, listHashtagPosts, listTrendingPosts, searchProfiles, toggleFollow } from "@/lib/social-feed-api";

const platforms = ["tiktok", "instagram", "facebook", "youtube"];
const tiers = ["nano", "micro", "mid", "macro"];

export default function DiscoverPage() {
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("");
  const [location, setLocation] = useState("");
  const [tier, setTier] = useState("");
  const [platform, setPlatform] = useState("");
  const [hashtag, setHashtag] = useState<string | null>(null);
  const filters = Object.fromEntries(Object.entries({ sector, location, tier, platform }).filter(([, value]) => value));
  const results = useQuery({ queryKey: ["discover-search", query, filters], queryFn: () => searchProfiles(query, filters), enabled: query.trim().length >= 2 });
  const trending = useQuery({ queryKey: ["social-trending"], queryFn: listTrendingPosts });
  const creators = useQuery({ queryKey: ["social-creators"], queryFn: listCreators });
  const hashtagPosts = useQuery({ queryKey: ["hashtag-posts", hashtag], queryFn: () => listHashtagPosts(hashtag!), enabled: Boolean(hashtag) });
  const clearFilters = () => { setSector(""); setLocation(""); setTier(""); setPlatform(""); };

  return (
    <RequireUserType allow={["brand", "influencer"]}>
      <DashboardShell title="Discover">
        <main className="mx-auto max-w-4xl space-y-5">
          <Card>
            <CardContent className="space-y-4 pt-6">
              <div><h1 className="font-semibold">Discover people and conversations</h1><p className="mt-1 text-sm text-muted-foreground">Find creators and brands by name, niche, audience, location, or connected platform.</p></div>
              <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name or @username" />
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                <Input value={sector} onChange={(event) => setSector(event.target.value)} placeholder="Sector or niche" />
                <Input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Location" />
                <select className="h-9 rounded-md border bg-background px-3 text-sm" value={tier} onChange={(event) => setTier(event.target.value)}><option value="">Any audience tier</option>{tiers.map((item) => <option key={item} value={item}>{item}</option>)}</select>
                <select className="h-9 rounded-md border bg-background px-3 text-sm" value={platform} onChange={(event) => setPlatform(event.target.value)}><option value="">Any platform</option>{platforms.map((item) => <option key={item} value={item}>{item}</option>)}</select>
              </div>
              {(sector || location || tier || platform) && <Button size="sm" variant="ghost" onClick={clearFilters}>Clear filters</Button>}
              {query.length > 0 && query.length < 2 && <p className="text-sm text-muted-foreground">Enter at least two characters to search.</p>}
              {query.length >= 2 && (results.isLoading ? <p className="text-sm text-muted-foreground">Searching...</p> : results.data?.length ? <div className="grid gap-2 sm:grid-cols-2">{results.data.map((profile) => <Link key={profile.id} href={`/social/profiles/${profile.id}`} className="rounded-md border p-3 text-sm transition-colors hover:bg-muted"><p className="font-medium">{profile.name}</p>{profile.username && <p className="text-muted-foreground">@{profile.username}</p>}</Link>)}</div> : <p className="text-sm text-muted-foreground">No matching profiles found.</p>)}
            </CardContent>
          </Card>

          <section className="space-y-3">
            <div><h2 className="font-semibold">Creators to follow</h2><p className="text-sm text-muted-foreground">Find other influencers, visit their profiles, and start a conversation.</p></div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {creators.data?.map((creator) => <CreatorCard key={creator.id} creator={creator} />)}
            </div>
          </section>

          {hashtag && <section className="space-y-3"><div className="flex items-center justify-between"><h2 className="font-semibold">#{hashtag}</h2><Button size="sm" variant="ghost" onClick={() => setHashtag(null)}>Close hashtag</Button></div>{hashtagPosts.isLoading ? <p className="text-sm text-muted-foreground">Loading posts...</p> : hashtagPosts.data?.length ? hashtagPosts.data.map((post) => <Card key={post.id}><CardContent className="space-y-2 pt-5"><Link href={`/social/profiles/${post.author.id}`} className="text-sm font-medium hover:underline">{post.author.name}</Link><p className="whitespace-pre-wrap text-sm">{post.body}</p></CardContent></Card>) : <p className="text-sm text-muted-foreground">No visible posts use this hashtag yet.</p>}</section>}

          <section className="space-y-3"><div><h2 className="font-semibold">Trending now</h2><p className="text-sm text-muted-foreground">Popular public conversations across Clout.</p></div>{trending.isLoading && <p className="text-sm text-muted-foreground">Loading trends...</p>}{trending.data?.map((post) => <Card key={post.id}><CardContent className="space-y-2 pt-5"><Link href={`/social/profiles/${post.author.id}`} className="text-sm font-medium hover:underline">{post.author.name}</Link><p className="whitespace-pre-wrap text-sm">{post.body}</p>{post.hashtags?.length ? <div className="flex flex-wrap gap-1">{post.hashtags.map((tag) => <Button key={tag} size="xs" variant="outline" onClick={() => setHashtag(tag)}>#{tag}</Button>)}</div> : null}<p className="text-xs text-muted-foreground">{post.like_count} likes · {post.comment_count} comments</p></CardContent></Card>)}</section>
        </main>
      </DashboardShell>
    </RequireUserType>
  );
}

function CreatorCard({ creator }: { creator: { id: string; name: string; username?: string | null } }) {
  const follow = useMutation({ mutationFn: () => toggleFollow(creator.id) });
  return <Card><CardContent className="space-y-3 pt-5"><Link href={`/social/profiles/${creator.id}`} className="block"><p className="font-medium hover:underline">{creator.name}</p>{creator.username && <p className="text-sm text-muted-foreground">@{creator.username}</p>}</Link><div className="grid grid-cols-2 gap-2"><Button size="sm" variant="outline" render={<Link href={`/messages?with=${creator.id}`}>Chat</Link>} /><Button size="sm" onClick={() => follow.mutate()} disabled={follow.isPending}>{follow.isPending ? "Following..." : "Follow"}</Button></div></CardContent></Card>;
}
