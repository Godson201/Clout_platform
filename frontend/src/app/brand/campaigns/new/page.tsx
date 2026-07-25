"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { AxiosError } from "axios";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { listAdvertisements } from "@/lib/advertisements-api";
import { createCampaign } from "@/lib/campaigns-api";

const PLATFORMS = ["tiktok", "instagram", "facebook", "youtube"] as const;
const TIERS = ["nano", "micro", "mid", "macro"] as const;

function NewCampaignForm() {
  const router = useRouter();
  const { data: readyAds, isLoading } = useQuery({
    queryKey: ["advertisements", "ready"],
    queryFn: () => listAdvertisements(1, 50, "ready"),
  });

  const [form, setForm] = useState({
    advertisement_id: "",
    platforms: [] as string[],
    target_views: 10000,
    tier: "micro",
    slot_count: 4,
    performance_window_days: 3,
    target_sector: "",
    target_location: "",
  });
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () =>
      createCampaign({
        advertisement_id: form.advertisement_id,
        platforms: form.platforms,
        target_views: form.target_views,
        tier: form.tier,
        slot_count: form.slot_count,
        performance_window_days: form.performance_window_days,
        target_sector: form.target_sector || undefined,
        target_location: form.target_location || undefined,
      }),
    onSuccess: (campaign) => router.push(`/brand/campaigns/${campaign.id}`),
    onError: (err) => {
      const axiosErr = err as AxiosError<{ detail?: string }>;
      setError(axiosErr.response?.data?.detail ?? "Could not create campaign.");
    },
  });

  function togglePlatform(platform: string) {
    setForm((f) => ({
      ...f,
      platforms: f.platforms.includes(platform) ? f.platforms.filter((p) => p !== platform) : [...f.platforms, platform],
    }));
  }

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading your ready advertisements...</p>;

  if (!readyAds || readyAds.items.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          You need at least one advertisement marked &quot;ready&quot; (with a processed video) before creating a
          campaign. Head to the Brand Toolkit to create one.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>New campaign</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-5"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            if (!form.advertisement_id) return setError("Choose an advertisement.");
            if (form.platforms.length === 0) return setError("Choose at least one platform.");
            createMutation.mutate();
          }}
        >
          <div className="space-y-2">
            <Label>Advertisement</Label>
            <Select
              value={form.advertisement_id}
              onValueChange={(v) => setForm({ ...form, advertisement_id: v ?? "" })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Choose a ready advertisement" />
              </SelectTrigger>
              <SelectContent>
                {readyAds.items.map((ad) => (
                  <SelectItem key={ad.id} value={ad.id}>
                    {ad.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Platforms (target views apply per platform)</Label>
            <div className="flex flex-wrap gap-4">
              {PLATFORMS.map((p) => (
                <label key={p} className="flex items-center gap-2 text-sm capitalize">
                  <Checkbox checked={form.platforms.includes(p)} onCheckedChange={() => togglePlatform(p)} />
                  {p}
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Target views (per platform)</Label>
              <Input
                type="number"
                min={1}
                value={form.target_views}
                onChange={(e) => setForm({ ...form, target_views: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <Label>Influencer tier</Label>
              <Select value={form.tier} onValueChange={(v) => setForm({ ...form, tier: v ?? form.tier })}>
                <SelectTrigger>
                  <SelectValue />
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

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Number of influencers (per platform)</Label>
              <Input
                type="number"
                min={1}
                max={50}
                value={form.slot_count}
                onChange={(e) => setForm({ ...form, slot_count: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <Label>Performance window (days)</Label>
              <Input
                type="number"
                min={1}
                max={30}
                value={form.performance_window_days}
                onChange={(e) => setForm({ ...form, performance_window_days: Number(e.target.value) })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Target sector (optional)</Label>
              <Input
                value={form.target_sector}
                onChange={(e) => setForm({ ...form, target_sector: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Target location (optional)</Label>
              <Input
                value={form.target_location}
                onChange={(e) => setForm({ ...form, target_location: e.target.value })}
              />
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating..." : "Create campaign"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function NewCampaignPage() {
  return (
    <RequireUserType allow={["brand"]}>
      <DashboardShell title="Create campaign">
        <NewCampaignForm />
      </DashboardShell>
    </RequireUserType>
  );
}
