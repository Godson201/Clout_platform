"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { Influencer } from "@/types/auth";

const TIERS = ["nano", "micro", "mid", "macro"] as const;

async function fetchMyInfluencer(): Promise<Influencer> {
  const { data } = await api.get<Influencer>("/influencers/me");
  return data;
}

function verificationVariant(status: Influencer["verification_status"]) {
  if (status === "approved") return "default" as const;
  if (status === "rejected") return "destructive" as const;
  return "secondary" as const;
}

function InfluencerProfileCard({ influencer }: { influencer: Influencer }) {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [form, setForm] = useState({
    display_name: influencer.display_name,
    sector: influencer.sector ?? "",
    location: influencer.location ?? "",
    bio: influencer.bio ?? "",
    follower_tier: influencer.follower_tier ?? "",
  });
  const [isSaving, setIsSaving] = useState(false);

  async function handleSave() {
    setIsSaving(true);
    try {
      await api.patch("/influencers/me", { ...form, follower_tier: form.follower_tier || null });
      await queryClient.invalidateQueries({ queryKey: ["influencers", "me"] });
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>@{influencer.username}</CardTitle>
        <Badge variant={verificationVariant(influencer.verification_status)} className="capitalize">
          {influencer.verification_status}
        </Badge>
      </CardHeader>
      <CardContent>
        {!isEditing ? (
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-muted-foreground">Display name</dt>
              <dd className="font-medium">{influencer.display_name}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Sector</dt>
              <dd className="font-medium">{influencer.sector ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Location</dt>
              <dd className="font-medium">{influencer.location ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Bio</dt>
              <dd className="font-medium">{influencer.bio ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Follower tier</dt>
              <dd className="font-medium capitalize">{influencer.follower_tier ?? "Not set"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Slot record</dt>
              <dd className="font-medium">
                {influencer.completed_slots_count} completed / {influencer.failed_slots_count} failed
              </dd>
            </div>
            <div className="col-span-2">
              <Button size="sm" variant="outline" onClick={() => setIsEditing(true)}>
                Edit profile
              </Button>
            </div>
          </dl>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Display name</Label>
                <Input
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Sector</Label>
                <Input value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Location</Label>
                <Input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Bio</Label>
                <Input value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Follower tier (self-reported)</Label>
                <Select
                  value={form.follower_tier || undefined}
                  onValueChange={(v) => setForm({ ...form, follower_tier: v ?? "" })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a tier" />
                  </SelectTrigger>
                  <SelectContent>
                    {TIERS.map((t) => (
                      <SelectItem key={t} value={t} className="capitalize">
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={handleSave} disabled={isSaving}>
                {isSaving ? "Saving..." : "Save changes"}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setIsEditing(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function InfluencerOverview() {
  const {
    data: influencer,
    isLoading,
    error,
  } = useQuery({ queryKey: ["influencers", "me"], queryFn: fetchMyInfluencer });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading profile...</p>;
  if (error || !influencer) return <p className="text-sm text-destructive">Could not load your profile.</p>;

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <InfluencerProfileCard influencer={influencer} />
      <Card>
        <CardHeader>
          <CardTitle>Marketplace</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Browse open campaign slots matched to your profile and claim up to 5 active at once.
          </p>
          <div className="flex gap-2">
            <Button size="sm" render={<Link href="/influencer/marketplace" />}>
              Browse marketplace
            </Button>
            <Button size="sm" variant="outline" render={<Link href="/influencer/slots" />}>
              My slots
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Connected accounts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Connect TikTok, Instagram, Facebook, or YouTube so you can post claimed slots' ads and track performance.
          </p>
          <Button size="sm" render={<Link href="/social-accounts" />}>
            Manage accounts
          </Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Earnings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            See your wallet balance, request a withdrawal to MTN MoMo, and track past payouts.
          </p>
          <Button size="sm" render={<Link href="/influencer/earnings" />}>
            View earnings
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default function InfluencerDashboardPage() {
  return (
    <RequireUserType allow={["influencer"]}>
      <DashboardShell title="Influencer overview">
        <InfluencerOverview />
      </DashboardShell>
    </RequireUserType>
  );
}
