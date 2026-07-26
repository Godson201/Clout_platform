"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listAdvertisements } from "@/lib/advertisements-api";
import type { AdvertisementStatus } from "@/types/advertisement";

function statusVariant(status: AdvertisementStatus) {
  if (status === "ready") return "success" as const;
  if (status === "archived") return "secondary" as const;
  return "outline" as const;
}

function AdvertisementLibrary() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["advertisements"],
    queryFn: () => listAdvertisements(),
  });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading advertisements...</p>;
  if (error) return <p className="text-sm text-destructive">Could not load advertisements.</p>;

  if (!data || data.items.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <p className="mb-4 text-sm text-muted-foreground">You haven&apos;t created any advertisements yet.</p>
          <Button render={<Link href="/brand/toolkit" />}>Open Brand Toolkit</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {data.items.map((ad) => (
        <Link key={ad.id} href={`/brand/ads/${ad.id}`}>
          <Card className="h-full transition-colors hover:border-primary">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">{ad.title}</CardTitle>
              <Badge variant={statusVariant(ad.status)} className="capitalize">
                {ad.status}
              </Badge>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {ad.duration_seconds ? `${ad.duration_seconds}s` : "No duration set"}
              </p>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

export default function BrandAdsPage() {
  return (
    <RequireUserType allow={["brand"]}>
      <DashboardShell title="Advertisement Library">
        <div className="mb-6 flex justify-end">
          <Button render={<Link href="/brand/toolkit" />}>+ New advertisement</Button>
        </div>
        <AdvertisementLibrary />
      </DashboardShell>
    </RequireUserType>
  );
}
