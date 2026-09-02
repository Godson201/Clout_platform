"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { AxiosError } from "axios";
import { BadgeCheck, ShieldCheck, Sparkles, TrendingUp } from "lucide-react";

import { ContinueWithGoogleButton } from "@/components/auth/continue-with-google-button";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { BackButton } from "@/components/ui/back-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login } from "@/lib/auth-api";
import { useAuthStore } from "@/store/auth-store";

const HIGHLIGHTS = [
  {
    icon: Sparkles,
    title: "Brand Toolkit built in",
    body: "Turn a template into a platform-ready short-form ad in minutes — no agency required.",
  },
  {
    icon: TrendingUp,
    title: "Real matching, real tracking",
    body: "Influencers get matched by sector, location, and track record — then performance is tracked automatically.",
  },
  {
    icon: ShieldCheck,
    title: "MTN MoMo escrow",
    body: "Campaign budgets sit in secure escrow and only release as delivery is verified.",
  },
  {
    icon: BadgeCheck,
    title: "Built for Rwanda",
    body: "Real province-to-village location data, so brands and creators can find each other locally.",
  },
];

function HeroPanel() {
  return (
    <div className="relative isolate hidden flex-1 flex-col justify-between overflow-hidden p-10 text-white lg:flex">
      <Image
        src="/images/clout-hero-creator-v1.png"
        alt="A creator filming a campaign with her phone"
        fill
        priority
        quality={90}
        sizes="50vw"
        className="object-cover object-[72%_center]"
      />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(145deg,rgba(3,22,38,0.80)_0%,rgba(3,22,38,0.48)_55%,rgba(3,22,38,0.12)_100%)]" />
      <div className="relative z-10 flex items-center justify-between">
        <img src="/clout-logo.png" alt="CLOUT" className="h-8 w-auto" />
        <ThemeToggle className="border-white/30 bg-transparent text-white hover:bg-white/10" />
      </div>
      <div className="relative z-10 animate-fade-in">
        <h1 className="mt-10 max-w-md text-4xl leading-tight font-semibold text-balance">
          Where brands and influencers actually connect.
        </h1>
        <p className="mt-4 max-w-md text-white/80">
          Campaigns, escrow payments, publishing, and performance tracking — one platform, from first
          match to final report.
        </p>
      </div>
      <div className="relative z-10 grid gap-5 sm:grid-cols-2">
        {HIGHLIGHTS.map(({ icon: Icon, title, body }) => (
          <div key={title} className="glass-panel rounded-[18px] p-4">
            <Icon className="size-5 text-brand-teal" />
            <p className="mt-2 text-sm font-medium">{title}</p>
            <p className="mt-1 text-xs text-white/75">{body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const { user, access_token } = await login(email, password);
      setSession(user, access_token);
      router.push(`/${user.user_type}/dashboard`);
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail?: string }>;
      setError(axiosErr.response?.data?.detail ?? "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-1">
      <HeroPanel />
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-4">
        <div className="flex w-full max-w-sm items-center justify-between">
          <BackButton fallbackHref="/" className="-ml-2" />
          <ThemeToggle className="lg:hidden" />
        </div>
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>Log in to CLOUT</CardTitle>
            <CardDescription>Brands, influencers, and admins sign in here.</CardDescription>
          </CardHeader>
          <CardContent>
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
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link href="/forgot-password" className="text-xs text-muted-foreground underline underline-offset-4">
                    Forgot password?
                  </Link>
                </div>
                <Input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Logging in..." : "Log in"}
              </Button>
            </form>
            <div className="my-4 flex items-center gap-3 text-xs text-muted-foreground">
              <span className="h-px flex-1 bg-border" />
              or
              <span className="h-px flex-1 bg-border" />
            </div>
            <ContinueWithGoogleButton label="Log in with Google" />
            <p className="mt-4 text-center text-sm text-muted-foreground">
              No account?{" "}
              <Link href="/register" className="underline underline-offset-4">
                Register as a brand or influencer
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
