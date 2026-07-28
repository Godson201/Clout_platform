import type { AdvertisementAsset, RenditionStatus } from "@/types/advertisement";

export function assetStatusVariant(status: AdvertisementAsset["status"] | RenditionStatus) {
  if (status === "ready") return "success" as const;
  if (status === "failed") return "destructive" as const;
  if (status === "processing") return "warning" as const;
  return "secondary" as const;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDuration(seconds: number): string {
  const total = Math.round(seconds);
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

export function moderationBadgeVariant(status: AdvertisementAsset["moderation_status"]) {
  if (status === "approved") return "success" as const;
  if (status === "rejected") return "destructive" as const;
  return "warning" as const;
}

export function moderationLabel(status: AdvertisementAsset["moderation_status"]) {
  if (status === "approved") return "Approved · shared with influencers";
  if (status === "rejected") return "Rejected";
  return "Pending admin review";
}

export function assetCaption(asset: AdvertisementAsset): string {
  const parts: string[] = [];
  if (asset.width && asset.height) parts.push(`${asset.width}×${asset.height}`);
  if (asset.duration_seconds) parts.push(formatDuration(asset.duration_seconds));
  parts.push(formatFileSize(asset.file_size_bytes));
  return parts.join(" · ");
}

export function AssetPreview({ asset }: { asset: AdvertisementAsset }) {
  if (asset.status !== "ready" || !asset.url) return null;

  if (asset.asset_type === "video") {
    return (
      <video
        controls
        preload="metadata"
        className="aspect-video w-full max-w-md rounded-lg border bg-black object-contain"
        src={asset.url}
      />
    );
  }
  if (asset.asset_type === "image" || asset.asset_type === "logo") {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={asset.url}
        alt={asset.original_filename}
        className="h-auto max-h-64 w-auto max-w-full rounded-lg border object-contain"
      />
    );
  }
  if (asset.asset_type === "audio" || asset.asset_type === "voiceover") {
    return <audio controls preload="metadata" className="w-full max-w-md" src={asset.url} />;
  }
  return null;
}
