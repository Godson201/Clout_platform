"use client";

import Link from "next/link";
import { useState } from "react";

import { BackButton } from "@/components/ui/back-button";
import { AuthPageVisualBackground } from "@/components/marketing/auth-page-visual-background";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { forgotPassword } from "@/lib/auth-api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await forgotPassword(email);
    } finally {
      // Always show the same success state, whether or not the email is
      // registered — the backend deliberately never reveals which.
      setIsSubmitting(false);
      setSent(true);
    }
  }

  return (
    <main className="relative isolate flex flex-1 flex-col items-center justify-center gap-4 overflow-hidden p-4">
      <AuthPageVisualBackground />
      <div className="relative z-10 w-full max-w-sm">
        <BackButton fallbackHref="/login" className="-ml-2 border border-white/25 bg-white/10 text-white hover:bg-white/20 hover:text-white" />
      </div>
      <Card className="relative z-10 w-full max-w-sm shadow-2xl">
        <CardHeader>
          <CardTitle>Reset your password</CardTitle>
          <CardDescription>We&apos;ll email you a link to choose a new one.</CardDescription>
        </CardHeader>
        <CardContent>
          {sent ? (
            <p className="text-sm text-muted-foreground">
              If <span className="font-medium text-foreground">{email}</span> is registered with CLOUT, a reset
              link is on its way — check your inbox (and spam folder).
            </p>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                />
              </div>
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Sending..." : "Send reset link"}
              </Button>
            </form>
          )}
          <p className="mt-4 text-center text-sm text-muted-foreground">
            <Link href="/login" className="underline underline-offset-4">
              Back to log in
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
