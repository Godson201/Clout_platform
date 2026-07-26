"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { hasLocationData, LocationMap } from "@/components/location/location-map";
import { RwandaLocationPicker } from "@/components/location/rwanda-location-picker";
import { ProfilePictureUpload } from "@/components/profile/profile-picture-upload";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { uploadBrandLogo } from "@/lib/profile-api";
import type { Brand } from "@/types/auth";

async function fetchMyBrand(): Promise<Brand> {
  const { data } = await api.get<Brand>("/brands/me");
  return data;
}

function verificationVariant(status: Brand["verification_status"]) {
  if (status === "approved") return "success" as const;
  if (status === "rejected") return "destructive" as const;
  if (status === "pending") return "warning" as const;
  return "secondary" as const;
}

function BrandProfileCard({ brand }: { brand: Brand }) {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [form, setForm] = useState({
    business_name: brand.business_name,
    sector: brand.sector ?? "",
    website: brand.website ?? "",
  });
  const [location, setLocation] = useState({
    province: brand.province ?? "",
    location: brand.location ?? "",
    admin_sector: brand.admin_sector ?? "",
    admin_cell: brand.admin_cell ?? "",
    admin_village: brand.admin_village ?? "",
    address_detail: brand.address_detail ?? "",
  });
  const [isSaving, setIsSaving] = useState(false);

  async function invalidate() {
    await queryClient.invalidateQueries({ queryKey: ["brands", "me"] });
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      await api.patch("/brands/me", { ...form, ...location });
      await invalidate();
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Business profile</CardTitle>
        <Badge variant={verificationVariant(brand.verification_status)} className="capitalize">
          {brand.verification_status}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <ProfilePictureUpload
          currentUrl={brand.logo_url}
          initials={brand.business_name.slice(0, 2).toUpperCase()}
          label="Logo"
          onUpload={async (file) => {
            await uploadBrandLogo(file);
            await invalidate();
          }}
        />
        {!isEditing ? (
          <>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-muted-foreground">Business name</dt>
                <dd className="font-medium">{brand.business_name}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Industry / niche</dt>
                <dd className="font-medium">{brand.sector ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Location</dt>
                <dd className="font-medium">
                  {[brand.address_detail, brand.admin_village, brand.admin_cell, brand.admin_sector, brand.location, brand.province]
                    .filter(Boolean)
                    .join(", ") || "—"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Website</dt>
                <dd className="font-medium">{brand.website ?? "—"}</dd>
              </div>
              <div className="col-span-2">
                <Button size="sm" variant="outline" onClick={() => setIsEditing(true)}>
                  Edit profile
                </Button>
              </div>
            </dl>
            {hasLocationData(brand) && (
              <div>
                <p className="mb-2 text-xs text-muted-foreground">
                  Shown to influencers so they can find your business — helpful for in-person collabs.
                </p>
                <LocationMap fields={brand} />
              </div>
            )}
          </>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Business name</Label>
                <Input
                  value={form.business_name}
                  onChange={(e) => setForm({ ...form, business_name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Industry / niche</Label>
                <Input value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} />
              </div>
              <div className="col-span-2 space-y-2">
                <Label>Website</Label>
                <Input value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Location</Label>
              <RwandaLocationPicker value={location} onChange={(patch) => setLocation({ ...location, ...patch })} />
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

function BrandOverview() {
  const { data: brand, isLoading, error } = useQuery({ queryKey: ["brands", "me"], queryFn: fetchMyBrand });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading profile...</p>;
  if (error || !brand) return <p className="text-sm text-destructive">Could not load your brand profile.</p>;

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <BrandProfileCard brand={brand} />
      <Card>
        <CardHeader>
          <CardTitle>Brand Toolkit</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Build short-form ads from templates and export them for TikTok, Instagram, Facebook, and YouTube.
          </p>
          <div className="flex gap-2">
            <Button size="sm" render={<Link href="/brand/toolkit" />}>
              Create an ad
            </Button>
            <Button size="sm" variant="outline" render={<Link href="/brand/ads" />}>
              Advertisement library
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Campaigns</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Turn a ready advertisement into a priced campaign, pay for it via MTN MoMo, and distribute it through
            matched influencers once escrow is funded.
          </p>
          <div className="flex gap-2">
            <Button size="sm" render={<Link href="/brand/campaigns/new" />}>
              Create a campaign
            </Button>
            <Button size="sm" variant="outline" render={<Link href="/brand/campaigns" />}>
              View campaigns
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
            Optionally connect your own TikTok, Instagram, Facebook, or YouTube account.
          </p>
          <Button size="sm" variant="outline" render={<Link href="/social-accounts" />}>
            Manage accounts
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default function BrandDashboardPage() {
  return (
    <RequireUserType allow={["brand"]}>
      <DashboardShell title="Brand overview">
        <BrandOverview />
      </DashboardShell>
    </RequireUserType>
  );
}
