"use client";

import { useMutation } from "@tanstack/react-query";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";
import type { AxiosError } from "axios";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { completeOAuthLogin } from "@/lib/oauth-login-api";
import { useAuthStore } from "@/store/auth-store";

/** Google's (or the mock consent page's) redirect lands here with
 * ?code=...&state=... — unlike social/callback (which connects a platform
 * to an *already logged-in* account), this callback is what establishes the
 * session in the first place, so it fires immediately rather than waiting on
 * any existing auth state. */
export default function OAuthLoginCallbackPage() {
  const params = useParams<{ provider: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);
  const hasRun = useRef(false);

  const mutation = useMutation({
    mutationFn: () => {
      const code = searchParams.get("code");
      const state = searchParams.get("state");
      if (!code || !state) throw new Error("Missing code or state in callback URL");
      return completeOAuthLogin(params.provider, code, state);
    },
    onSuccess: (data) => {
      setSession(data.user, data.access_token);
      router.replace(`/${data.user.user_type}/dashboard`);
    },
  });

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;
    mutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const errorDetail = (mutation.error as AxiosError<{ detail?: string }>)?.response?.data?.detail;
  const noAccountYet = (mutation.error as AxiosError)?.response?.status === 404;

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="capitalize">Signing in with {params.provider}...</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {mutation.isPending && <p className="text-muted-foreground">Confirming with CLOUT...</p>}
          {mutation.isError && (
            <>
              <p className="text-destructive">{errorDetail ?? "Could not complete sign-in."}</p>
              {noAccountYet && (
                <p className="text-muted-foreground">
                  Head back to{" "}
                  <a href="/register" className="underline underline-offset-4">
                    the register page
                  </a>{" "}
                  and choose Brand or Influencer first, then continue with Google from there.
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
