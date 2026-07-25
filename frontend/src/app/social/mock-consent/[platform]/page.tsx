"use client";

import { useParams, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Stands in for a real provider's OAuth consent screen when
 * SOCIAL_OAUTH_MODE=mock (see backend app/services/social/mock.py) — there is
 * no real TikTok/Meta/Google app to redirect to without real credentials, so
 * this page plays that role instead, keeping the connect flow fully clickable
 * end-to-end in a browser rather than dead-ending on a fake external domain.
 * Never reached once SOCIAL_OAUTH_MODE=live, since the authorization_url then
 * points at the real provider.
 */
export default function MockConsentPage() {
  const params = useParams<{ platform: string }>();
  const searchParams = useSearchParams();

  const state = searchParams.get("state");
  const redirectUri = searchParams.get("redirect_uri");
  const code = searchParams.get("code");

  const valid = state && redirectUri && code;

  function approve() {
    if (!valid) return;
    const url = new URL(redirectUri);
    url.searchParams.set("code", code);
    url.searchParams.set("state", state);
    window.location.href = url.toString();
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="capitalize">{params.platform} (simulated)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p className="text-muted-foreground">
            This stands in for {params.platform}&apos;s real consent screen — CLOUT doesn&apos;t have live API
            access to this platform yet, so authorization is simulated locally.
          </p>
          {!valid ? (
            <p className="text-destructive">Missing or invalid OAuth parameters.</p>
          ) : (
            <p>CLOUT would like to post campaign ads and read basic profile info on your behalf.</p>
          )}
          <div className="flex gap-2">
            <Button onClick={approve} disabled={!valid}>
              Approve
            </Button>
            <Button variant="outline" onClick={() => window.history.back()}>
              Cancel
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
