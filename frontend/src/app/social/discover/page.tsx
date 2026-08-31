"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { searchProfiles, type SocialPost } from "@/lib/social-feed-api";

export default function DiscoverPage() {
  const [query, setQuery] = useState("");
  const results = useQuery({ queryKey: ["discover-search", query], queryFn: () => searchProfiles(query), enabled: query.trim().length >= 2 });
  const trending = useQuery({ queryKey: ["social-trending"], queryFn: async () => (await api.get<SocialPost[]>("/social/trending")).data });
  return <RequireUserType allow={["brand", "influencer"]}><DashboardShell title="Discover"><div className="mx-auto max-w-3xl space-y-5"><Card><CardContent className="space-y-3 pt-6"><h1 className="font-semibold">Find creators, brands, and conversations</h1><input className="h-10 w-full rounded-md border bg-background px-3 text-sm" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search name or @username" />{query.length >= 2 && (results.data?.length ? <div className="space-y-2">{results.data.map(profile => <Link key={profile.id} href={`/social/profiles/${profile.id}`} className="block rounded-md border p-3 text-sm hover:bg-muted"><span className="font-medium">{profile.name}</span>{profile.username ? <span className="text-muted-foreground"> @{profile.username}</span> : null}</Link>)}</div> : <p className="text-sm text-muted-foreground">No profiles found.</p>)}</CardContent></Card><section className="space-y-3"><h2 className="font-semibold">Trending now</h2>{trending.data?.map(post => <Card key={post.id}><CardContent className="pt-5"><Link href={`/social/profiles/${post.author.id}`} className="text-sm font-medium hover:underline">{post.author.name}</Link><p className="mt-2 whitespace-pre-wrap text-sm">{post.body}</p><p className="mt-2 text-xs text-muted-foreground">{post.like_count} likes · {post.comment_count} comments</p></CardContent></Card>)}{trending.isLoading && <p className="text-sm text-muted-foreground">Loading trends...</p>}</section></div></DashboardShell></RequireUserType>;
}
