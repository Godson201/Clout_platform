"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import type { AxiosError } from "axios";

import { BackButton } from "@/components/ui/back-button";
import { AuthPageVisualBackground } from "@/components/marketing/auth-page-visual-background";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getPasswordResetPrompt, resetPassword } from "@/lib/auth-api";

function ResetPasswordForm({ token }: { token: string }) {
  const { data: prompt, isLoading, isError } = useQuery({
    queryKey: ["password-reset-prompt", token],
    queryFn: () => getPasswordResetPrompt(token),
    retry: false,
  });

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [securityAnswer, setSecurityAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const passwordsMatch = newPassword === confirmPassword;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!passwordsMatch) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await resetPassword({
        token,
        new_password: newPassword,
        ...(prompt?.security_question ? { security_answer: securityAnswer } : {}),
      });
      setDone(true);
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail?: string }>;
      setError(axiosErr.response?.data?.detail ?? "Could not reset your password. The link may have expired.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) return <p className="text-sm text-muted-foreground">Checking your link...</p>;

  if (isError) {
    return (
      <p className="text-sm text-destructive">
        This reset link is invalid or has expired. Request a new one from the{" "}
        <Link href="/forgot-password" className="underline underline-offset-4">
          forgot password
        </Link>{" "}
        page.
      </p>
    );
  }

  if (done) {
    return (
      <p className="text-sm text-muted-foreground">
        Your password has been updated. You can now{" "}
        <Link href="/login" className="underline underline-offset-4">
          log in
        </Link>{" "}
        with it.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="new_password">New password</Label>
        <Input
          id="new_password"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="confirm_password">Confirm new password</Label>
        <Input
          id="confirm_password"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          aria-invalid={confirmPassword.length > 0 && !passwordsMatch}
        />
        {confirmPassword.length > 0 && !passwordsMatch && (
          <p className="text-xs text-destructive">Passwords don&apos;t match.</p>
        )}
      </div>
      {prompt?.security_question && (
        <div className="space-y-2 rounded-lg border p-3">
          <Label htmlFor="security_answer">{prompt.security_question}</Label>
          <p className="text-xs text-muted-foreground">Confirms it&apos;s really you before changing the password.</p>
          <Input
            id="security_answer"
            required
            value={securityAnswer}
            onChange={(e) => setSecurityAnswer(e.target.value)}
          />
        </div>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" className="w-full" disabled={isSubmitting || !passwordsMatch}>
        {isSubmitting ? "Updating..." : "Update password"}
      </Button>
    </form>
  );
}

function ResetPasswordCardBody() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  if (!token) {
    return (
      <p className="text-sm text-destructive">
        Missing reset token. Use the link from your email, or request a new one from{" "}
        <Link href="/forgot-password" className="underline underline-offset-4">
          here
        </Link>
        .
      </p>
    );
  }

  return <ResetPasswordForm token={token} />;
}

export default function ResetPasswordPage() {
  return (
    <main className="relative isolate flex flex-1 flex-col items-center justify-center gap-4 overflow-hidden p-4">
      <AuthPageVisualBackground />
      <div className="relative z-10 w-full max-w-sm">
        <BackButton fallbackHref="/login" className="-ml-2 border border-white/25 bg-white/10 text-white hover:bg-white/20 hover:text-white" />
      </div>
      <Card className="relative z-10 w-full max-w-sm shadow-2xl">
        <CardHeader>
          <CardTitle>Choose a new password</CardTitle>
          <CardDescription>Make it something you haven&apos;t used before.</CardDescription>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<p className="text-sm text-muted-foreground">Loading...</p>}>
            <ResetPasswordCardBody />
          </Suspense>
        </CardContent>
      </Card>
    </main>
  );
}
