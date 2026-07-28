"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Heart, Link2, MessageCircle } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  addAssetComment,
  getAssetLikeStatus,
  listAssetComments,
  toggleAssetLike,
} from "@/lib/asset-comments-api";
import { cn } from "@/lib/utils";

function timeAgo(iso: string): string {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function AssetEngagement({ assetId, assetUrl }: { assetId: string; assetUrl: string | null }) {
  const queryClient = useQueryClient();
  const [showComments, setShowComments] = useState(false);
  const [draft, setDraft] = useState("");
  const [copied, setCopied] = useState(false);

  const { data: likeStatus } = useQuery({
    queryKey: ["asset-like", assetId],
    queryFn: () => getAssetLikeStatus(assetId),
  });
  const { data: comments } = useQuery({
    queryKey: ["asset-comments", assetId],
    queryFn: () => listAssetComments(assetId),
    enabled: showComments,
  });

  const likeMutation = useMutation({
    mutationFn: () => toggleAssetLike(assetId),
    onSuccess: (data) => queryClient.setQueryData(["asset-like", assetId], data),
  });
  const commentMutation = useMutation({
    mutationFn: () => addAssetComment(assetId, draft),
    onSuccess: () => {
      setDraft("");
      queryClient.invalidateQueries({ queryKey: ["asset-comments", assetId] });
    },
  });

  async function handleShare() {
    if (!assetUrl) return;
    await navigator.clipboard.writeText(assetUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-3 border-t pt-3">
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <button
          type="button"
          onClick={() => likeMutation.mutate()}
          disabled={likeMutation.isPending}
          className={cn(
            "flex items-center gap-1.5 transition-colors hover:text-primary",
            likeStatus?.liked && "text-primary",
          )}
        >
          <Heart className={cn("size-4", likeStatus?.liked && "fill-current")} />
          {likeStatus?.like_count ?? 0}
        </button>
        <button
          type="button"
          onClick={() => setShowComments((v) => !v)}
          className="flex items-center gap-1.5 transition-colors hover:text-primary"
        >
          <MessageCircle className="size-4" />
          Comments
        </button>
        <button
          type="button"
          onClick={handleShare}
          disabled={!assetUrl}
          className="flex items-center gap-1.5 transition-colors hover:text-primary disabled:opacity-50"
        >
          <Link2 className="size-4" />
          {copied ? "Copied!" : "Share"}
        </button>
      </div>

      {showComments && (
        <div className="space-y-3">
          <ul className="space-y-2">
            {comments?.length === 0 && <p className="text-xs text-muted-foreground">No comments yet.</p>}
            {comments?.map((c) => (
              <li key={c.id} className="rounded-lg bg-muted/50 p-2 text-sm">
                <div className="flex items-center gap-1.5">
                  <span className="font-medium">{c.author_name}</span>
                  {c.author_is_admin && <span className="text-xs text-primary">(Admin)</span>}
                  <span className="ml-auto text-xs text-muted-foreground">{timeAgo(c.created_at)}</span>
                </div>
                <p className="text-muted-foreground">{c.body}</p>
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Leave feedback..."
              className="min-h-9"
            />
            <Button
              size="sm"
              disabled={draft.trim().length === 0 || commentMutation.isPending}
              onClick={() => commentMutation.mutate()}
            >
              Post
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
