"use client";

/* Natural-language explanatory copy intentionally contains contractions. */
/* eslint-disable react/no-unescaped-entities */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import type { AxiosError } from "axios";

import { AssetPreview, assetCaption } from "@/components/advertisements/asset-preview";
import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { browseApprovedMedia, browseMarketplace, claimSlot, type MarketplaceFilters } from "@/lib/campaigns-api";
import type { MarketplaceSlot } from "@/types/campaign";

const PLATFORMS = ["tiktok", "instagram", "facebook", "youtube"];
const TIERS = ["nano", "micro", "mid", "macro"];

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-20 text-muted-foreground">{label}</span>
      <div className="h-1.5 flex-1 rounded-full bg-muted">
        <div className="h-1.5 rounded-full bg-primary" style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
      <span className="w-8 text-right text-muted-foreground">{Math.round(value * 100)}%</span>
    </div>
  );
}

function SlotCard({ slot }: { slot: MarketplaceSlot }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const claimMutation = useMutation({
    mutationFn: () => claimSlot(slot.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["marketplace"] });
      await queryClient.invalidateQueries({ queryKey: ["slots", "mine"] });
    },
    onError: (err) => {
      const axiosErr = err as AxiosError<{ detail?: string }>;
      setError(axiosErr.response?.data?.detail ?? "Could not claim this slot.");
    },
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle className="text-base">{slot.advertisement_title}</CardTitle>
          <p className="text-xs text-muted-foreground">{slot.brand_name}</p>
        </div>
        <div className="flex items-center gap-1">
          {slot.recovery_generation > 0 && (
            <Badge variant="outline" title="This slot was recycled from an earlier delivery shortfall">
              Recovered
            </Badge>
          )}
          <Badge className="capitalize">{slot.platform}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-sm text-muted-foreground">
          <p>{slot.target_views.toLocaleString()} views target</p>
          <p className="font-medium text-foreground">{Number(slot.budget_allocated).toLocaleString()} budget</p>
          <p className="capitalize">Tier: {slot.tier}</p>
        </div>
        <div className="space-y-1 rounded-md border p-2">
          <ScoreBar label="Sector" value={slot.match_score.sector_score} />
          <ScoreBar label="Location" value={slot.match_score.location_score} />
          <ScoreBar label="Tier fit" value={slot.match_score.tier_score} />
          <ScoreBar label="Reliability" value={slot.match_score.reliability_score} />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Base match</span>
            <span>{Math.round(slot.match_score.total * 100)}%</span>
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Segment track record</span>
            <span>
              {slot.historical_boost > 1 ? "+" : slot.historical_boost < 1 ? "-" : ""}
              {Math.abs(Math.round((slot.historical_boost - 1) * 100))}%
            </span>
          </div>
          <div className="mt-1 flex items-center justify-between text-xs font-medium">
            <span>Overall match</span>
            <span>{Math.round(slot.final_score * 100)}%</span>
          </div>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button size="sm" className="w-full" onClick={() => claimMutation.mutate()} disabled={claimMutation.isPending}>
          {claimMutation.isPending ? "Claiming..." : "Claim this slot"}
        </Button>
      </CardContent>
    </Card>
  );
}

function MarketplaceBrowser() {
  const [filters, setFilters] = useState<MarketplaceFilters>({});

  const { data, isLoading, error } = useQuery({
    queryKey: ["marketplace", filters],
    queryFn: () => browseMarketplace(filters),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-3">
        <Select
          value={filters.platform ?? "all"}
          onValueChange={(v) => setFilters({ ...filters, platform: !v || v === "all" ? undefined : v })}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Platform" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All platforms</SelectItem>
            {PLATFORMS.map((p) => (
              <SelectItem key={p} value={p} className="capitalize">
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={filters.tier ?? "all"}
          onValueChange={(v) => setFilters({ ...filters, tier: !v || v === "all" ? undefined : v })}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Tier" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All tiers</SelectItem>
            {TIERS.map((t) => (
              <SelectItem key={t} value={t} className="capitalize">
                {t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Loading marketplace...</p>}
      {error && <p className="text-sm text-destructive">Could not load the marketplace.</p>}
      {data && data.length === 0 && (
        <p className="text-sm text-muted-foreground">No open slots match these filters right now.</p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.map((slot) => <SlotCard key={slot.id} slot={slot} />)}
      </div>
    </div>
  );
}

function BrandMediaGallery() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["marketplace", "media"],
    queryFn: browseApprovedMedia,
  });

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Approved creative from every brand on CLOUT — see exactly what they're looking for before you claim a slot.
      </p>
      {isLoading && <p className="text-sm text-muted-foreground">Loading brand media...</p>}
      {error && <p className="text-sm text-destructive">Could not load brand media.</p>}
      {data && data.length === 0 && (
        <p className="text-sm text-muted-foreground">No approved brand media yet — check back soon.</p>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.map((item) => (
          <Card key={item.id}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div>
                <CardTitle className="text-base">{item.advertisement_title}</CardTitle>
                <p className="text-xs text-muted-foreground">{item.brand_name}</p>
              </div>
              <Badge className="capitalize">{item.asset_type}</Badge>
            </CardHeader>
            <CardContent className="space-y-2">
              <AssetPreview asset={item} />
              <p className="text-xs text-muted-foreground">{assetCaption(item)}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function MarketplaceTabs() {
  const searchParams = useSearchParams();
  const defaultTab = searchParams.get("tab") === "media" ? "media" : "slots";

  return (
    <Tabs defaultValue={defaultTab}>
      <TabsList>
        <TabsTrigger value="slots">Open slots</TabsTrigger>
        <TabsTrigger value="media">Brand media</TabsTrigger>
      </TabsList>
      <TabsContent value="slots" className="mt-4">
        <MarketplaceBrowser />
      </TabsContent>
      <TabsContent value="media" className="mt-4">
        <BrandMediaGallery />
      </TabsContent>
    </Tabs>
  );
}

export default function MarketplacePage() {
  return (
    <RequireUserType allow={["influencer"]}>
      <DashboardShell title="Marketplace">
        <Suspense fallback={<p className="text-sm text-muted-foreground">Loading marketplace...</p>}>
          <MarketplaceTabs />
        </Suspense>
      </DashboardShell>
    </RequireUserType>
  );
}
