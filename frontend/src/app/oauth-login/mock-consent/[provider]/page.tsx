"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * Stands in for a real provider's "Sign in with Google" screen when no real
 * GOOGLE_CLIENT_ID/SECRET are configured (see backend
 * app/services/oauth_login.py) — since there's no real Google app to
 * redirect to, this lets a developer type the email/name they want to sign
 * in as, which becomes the account's identity, then hands the browser back
 * to the callback exactly like a real provider would (?code=...&state=...).
 * Never reached once real Google credentials are set.
 */
export default function OAuthLoginMockConsentPage() {
  const params = useParams<{ provider: string }>();
  const searchParams = useSearchParams();

  const state = searchParams.get("state");
  const redirectUri = searchParams.get("redirect_uri");
  const valid = Boolean(state && redirectUri);

  const [email, setEmail] = useState("");
  const [name, setName] = useState("");

  function approve() {
    if (!valid || !email.trim()) return;
    // URL-safe base64 (-/_ instead of +//), matching Python's
    // base64.urlsafe_b64decode on the backend — plain btoa() output isn't
    // URL-safe and would corrupt the code when it round-trips as a query param.
    const json = JSON.stringify({ email: email.trim(), name: name.trim() || null });
    const code = btoa(unescape(encodeURIComponent(json))).replace(/\+/g, "-").replace(/\//g, "_");
    const url = new URL(redirectUri as string);
    url.searchParams.set("code", code);
    url.searchParams.set("state", state as string);
    window.location.href = url.toString();
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="capitalize">{params.provider} sign-in (simulated)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p className="text-muted-foreground">
            CLOUT doesn&apos;t have a real {params.provider} app configured yet, so this stands in for it — whatever
            you type here becomes the signed-in account&apos;s identity.
          </p>
          {!valid ? (
            <p className="text-destructive">Missing or invalid OAuth parameters.</p>
          ) : (
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="mock-email">Email</Label>
                <Input
                  id="mock-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="mock-name">Name</Label>
                <Input id="mock-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" />
              </div>
            </div>
          )}
          <div className="flex gap-2">
            <Button onClick={approve} disabled={!valid || !email.trim()}>
              Continue
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
