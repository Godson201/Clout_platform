"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef } from "react";
import type { AxiosError } from "axios";

import { BackButton } from "@/components/ui/back-button";
import { AuthPageVisualBackground } from "@/components/marketing/auth-page-visual-background";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { verifyEmail } from "@/lib/auth-api";

function VerifyEmailCardBody() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const hasRun = useRef(false);

  const mutation = useMutation({
    mutationFn: () => verifyEmail(token as string),
  });

  useEffect(() => {
    if (hasRun.current || !token) return;
    hasRun.current = true;
    mutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <>
      {!token && <p className="text-destructive">Missing verification token.</p>}
      {token && mutation.isPending && <p className="text-muted-foreground">Confirming...</p>}
      {token && mutation.isSuccess && (
        <p className="text-muted-foreground">
          Your email is confirmed.{" "}
          <Link href="/login" className="underline underline-offset-4">
            Log in
          </Link>{" "}
          to continue.
        </p>
      )}
      {token && mutation.isError && (
        <p className="text-destructive">
          {(mutation.error as AxiosError<{ detail?: string }>)?.response?.data?.detail ??
            "This confirmation link is invalid or has expired."}
        </p>
      )}
    </>
  );
}

export default function VerifyEmailPage() {
  return (
    <main className="relative isolate flex flex-1 flex-col items-center justify-center gap-4 overflow-hidden p-4">
      <AuthPageVisualBackground />
      <div className="relative z-10 w-full max-w-sm">
        <BackButton fallbackHref="/login" className="-ml-2 border border-white/25 bg-white/10 text-white hover:bg-white/20 hover:text-white" />
      </div>
      <Card className="relative z-10 w-full max-w-sm shadow-2xl">
        <CardHeader>
          <CardTitle>Email confirmation</CardTitle>
          <CardDescription>Confirming your CLOUT account email.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Suspense fallback={<p className="text-muted-foreground">Loading...</p>}>
            <VerifyEmailCardBody />
          </Suspense>
        </CardContent>
      </Card>
    </main>
  );
}
