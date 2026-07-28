"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { AxiosError } from "axios";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { AssetEngagement } from "@/components/advertisements/asset-engagement";
import {
  AssetPreview,
  assetCaption,
  assetStatusVariant,
  moderationBadgeVariant,
  moderationLabel,
} from "@/components/advertisements/asset-preview";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  deleteAdvertisementAsset,
  getAdvertisement,
  updateAdvertisement,
  uploadAdvertisementAsset,
} from "@/lib/advertisements-api";
import type { AdvertisementAsset, AdvertisementDetail, AssetType } from "@/types/advertisement";

const ASSET_TYPES: { type: AssetType; label: string; accept: string }[] = [
  { type: "video", label: "Video", accept: "video/*" },
  { type: "image", label: "Image", accept: "image/*" },
  { type: "logo", label: "Logo", accept: "image/*" },
  { type: "audio", label: "Audio / jingle", accept: "audio/*" },
  { type: "voiceover", label: "Voice-over", accept: "audio/*" },
];

function isStillProcessing(ad: AdvertisementDetail | undefined): boolean {
  if (!ad) return false;
  return ad.assets.some(
    (a) => a.status === "uploaded" || a.status === "processing" || a.renditions.some((r) => r.status === "pending" || r.status === "processing"),
  );
}

function AssetCard({ asset, advertisementId }: { asset: AdvertisementAsset; advertisementId: string }) {
  const queryClient = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: () => deleteAdvertisementAsset(advertisementId, asset.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["advertisement", advertisementId] }),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-sm capitalize">{asset.asset_type}</CardTitle>
          <p className="text-xs text-muted-foreground">{asset.original_filename}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={assetStatusVariant(asset.status)} className="capitalize">
            {asset.status}
          </Badge>
          <Button size="sm" variant="ghost" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
            Remove
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {asset.error_message && <p className="text-sm text-destructive">{asset.error_message}</p>}
        <AssetPreview asset={asset} />
        {asset.status === "ready" && (
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs text-muted-foreground">{assetCaption(asset)}</p>
            <Badge variant={moderationBadgeVariant(asset.moderation_status)} className="text-[10px]">
              {moderationLabel(asset.moderation_status)}
            </Badge>
          </div>
        )}
        {asset.moderation_status === "rejected" && asset.moderation_note && (
          <p className="text-sm text-destructive">Admin feedback: {asset.moderation_note}</p>
        )}
        {asset.asset_type === "video" && asset.renditions.length > 0 && (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {asset.renditions.map((r) => (
              <div key={r.id} className="rounded-md border p-2 text-xs">
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-medium capitalize">{r.platform}</span>
                  <Badge variant={assetStatusVariant(r.status)} className="capitalize">
                    {r.status}
                  </Badge>
                </div>
                {r.status === "ready" && (
                  <p className="text-muted-foreground">
                    {r.width}x{r.height} · {r.duration_seconds?.toFixed(1)}s
                  </p>
                )}
                {r.status === "failed" && r.error_message && (
                  <p className="text-destructive">{r.error_message}</p>
                )}
              </div>
            ))}
          </div>
        )}
        <AssetEngagement assetId={asset.id} assetUrl={asset.url} />
      </CardContent>
    </Card>
  );
}

function UploadButtons({ advertisementId }: { advertisementId: string }) {
  const queryClient = useQueryClient();
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadingType, setUploadingType] = useState<AssetType | null>(null);

  const uploadMutation = useMutation({
    mutationFn: ({ type, file }: { type: AssetType; file: File }) =>
      uploadAdvertisementAsset(advertisementId, type, file),
    onMutate: ({ type }) => {
      setUploadError(null);
      setUploadingType(type);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["advertisement", advertisementId] }),
    onError: (err) => {
      const axiosErr = err as AxiosError<{ detail?: string }>;
      setUploadError(axiosErr.response?.data?.detail ?? "Upload failed.");
    },
    onSettled: () => setUploadingType(null),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Upload media</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {ASSET_TYPES.map(({ type, label, accept }) => (
            <div key={type}>
              <input
                ref={(el) => {
                  inputRefs.current[type] = el;
                }}
                type="file"
                accept={accept}
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) uploadMutation.mutate({ type, file });
                  e.target.value = "";
                }}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={uploadingType !== null}
                onClick={() => inputRefs.current[type]?.click()}
              >
                {uploadingType === type ? "Uploading..." : `Upload ${label}`}
              </Button>
            </div>
          ))}
        </div>
        {uploadError && <p className="mt-2 text-sm text-destructive">{uploadError}</p>}
        <p className="mt-2 text-xs text-muted-foreground">
          Video uploads are automatically transcoded for TikTok, Instagram, Facebook, and YouTube.
        </p>
      </CardContent>
    </Card>
  );
}

function AdEditor({ advertisementId }: { advertisementId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: ad, isLoading, error } = useQuery({
    queryKey: ["advertisement", advertisementId],
    queryFn: () => getAdvertisement(advertisementId),
    refetchInterval: (query) => (isStillProcessing(query.state.data) ? 2000 : false),
  });

  const [form, setForm] = useState<{
    title: string;
    script_text: string;
    cta_text: string;
    hashtags: string;
    duration_seconds: number;
  } | null>(null);

  useEffect(() => {
    if (form === null && ad) {
      setForm({
        title: ad.title,
        script_text: ad.script_text ?? "",
        cta_text: ad.cta_text ?? "",
        hashtags: ad.hashtags.join(" "),
        duration_seconds: ad.duration_seconds ?? 30,
      });
    }
  }, [ad, form]);

  const saveMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateAdvertisement>[1]) => updateAdvertisement(advertisementId, payload),
    onSuccess: (updated) => queryClient.setQueryData(["advertisement", advertisementId], updated),
  });

  const markReadyMutation = useMutation({
    mutationFn: () => updateAdvertisement(advertisementId, { status: "ready" }),
    onSuccess: (updated) => queryClient.setQueryData(["advertisement", advertisementId], updated),
  });

  if (isLoading || !ad || !form) return <p className="text-sm text-muted-foreground">Loading advertisement...</p>;
  if (error) return <p className="text-sm text-destructive">Could not load this advertisement.</p>;

  const isArchived = ad.status === "archived";
  const hasReadyVideo = ad.assets.some((a) => a.asset_type === "video" && a.status === "ready");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => router.push("/brand/ads")}>
          ← Back to library
        </Button>
        <div className="flex items-center gap-2">
          <Badge className="capitalize">{ad.status}</Badge>
          {ad.status === "draft" && (
            <Button
              size="sm"
              disabled={!hasReadyVideo || markReadyMutation.isPending}
              onClick={() => markReadyMutation.mutate()}
              title={hasReadyVideo ? undefined : "Upload and process a video first"}
            >
              Mark ready
            </Button>
          )}
        </div>
      </div>

      {markReadyMutation.isError && (
        <p className="text-sm text-destructive">
          {((markReadyMutation.error as AxiosError<{ detail?: string }>).response?.data?.detail) ??
            "Could not mark ready."}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Creative details</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              saveMutation.mutate({
                title: form.title,
                script_text: form.script_text || undefined,
                cta_text: form.cta_text || undefined,
                hashtags: form.hashtags.split(/\s+/).filter(Boolean),
                duration_seconds: form.duration_seconds,
              });
            }}
          >
            <div className="space-y-2">
              <Label>Title</Label>
              <Input
                value={form.title}
                disabled={isArchived}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Script</Label>
              <Input
                value={form.script_text}
                disabled={isArchived}
                onChange={(e) => setForm({ ...form, script_text: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Call to action</Label>
                <Input
                  value={form.cta_text}
                  disabled={isArchived}
                  onChange={(e) => setForm({ ...form, cta_text: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Duration (seconds)</Label>
                <Input
                  type="number"
                  min={5}
                  max={180}
                  value={form.duration_seconds}
                  disabled={isArchived}
                  onChange={(e) => setForm({ ...form, duration_seconds: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Hashtags (space-separated)</Label>
              <Input
                value={form.hashtags}
                disabled={isArchived}
                onChange={(e) => setForm({ ...form, hashtags: e.target.value })}
              />
            </div>
            {!isArchived && (
              <Button type="submit" disabled={saveMutation.isPending}>
                {saveMutation.isPending ? "Saving..." : "Save changes"}
              </Button>
            )}
          </form>
        </CardContent>
      </Card>

      {!isArchived && <UploadButtons advertisementId={advertisementId} />}

      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground">Assets</h2>
        {ad.assets.length === 0 && <p className="text-sm text-muted-foreground">No media uploaded yet.</p>}
        {ad.assets.map((asset) => (
          <AssetCard key={asset.id} asset={asset} advertisementId={advertisementId} />
        ))}
      </div>
    </div>
  );
}

export default function BrandAdEditorPage() {
  const params = useParams<{ id: string }>();

  return (
    <RequireUserType allow={["brand"]}>
      <DashboardShell title="Edit advertisement">
        <AdEditor advertisementId={params.id} />
      </DashboardShell>
    </RequireUserType>
  );
}
