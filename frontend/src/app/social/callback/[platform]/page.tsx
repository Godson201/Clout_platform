"use client";

import { useMutation } from "@tanstack/react-query";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";
import type { AxiosError } from "axios";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { completeOAuthCallback } from "@/lib/social-api";

/** Every OAuth provider (real or the mock consent page) redirects the user's
 * browser here with ?code=...&state=... — this exchanges that for a connected
 * SocialAccount and sends the user back to the accounts page. */
export default function SocialOAuthCallbackPage() {
  const params = useParams<{ platform: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const hasRun = useRef(false);

  const mutation = useMutation({
    mutationFn: () => {
      const code = searchParams.get("code");
      const state = searchParams.get("state");
      if (!code || !state) throw new Error("Missing code or state in callback URL");
      return completeOAuthCallback(params.platform, code, state);
    },
    onSuccess: () => {
      router.replace("/social-accounts");
    },
  });

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;
    mutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="capitalize">Connecting {params.platform}...</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {mutation.isPending && <p className="text-muted-foreground">Confirming with CLOUT...</p>}
          {mutation.isError && (
            <p className="text-destructive">
              {(mutation.error as AxiosError<{ detail?: string }>)?.response?.data?.detail ??
                "Could not complete the connection."}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
