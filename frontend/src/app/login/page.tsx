"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { AxiosError } from "axios";
import { ArrowRight, BadgeCheck, LockKeyhole, ShieldCheck, Sparkles, TrendingUp } from "lucide-react";

import { ContinueWithGoogleButton } from "@/components/auth/continue-with-google-button";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { BackButton } from "@/components/ui/back-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login } from "@/lib/auth-api";
import { useAuthStore } from "@/store/auth-store";

const HIGHLIGHTS = [
  { icon: Sparkles, title: "Create campaigns", body: "Bring every approved asset and brief together in one place." },
  { icon: TrendingUp, title: "Grow with clarity", body: "Track engagement, delivery, and campaign performance as it happens." },
  { icon: ShieldCheck, title: "Work with confidence", body: "Verified accounts, secure payments, and clear collaboration." },
];

function BrandStory() {
  return (
    <section className="relative hidden min-h-screen flex-1 overflow-hidden px-10 py-9 text-white lg:flex lg:flex-col">
      <Image src="/images/clout-login-creator-v1.png" alt="A CLOUT creator preparing a product campaign" fill priority quality={90} sizes="50vw" className="object-cover object-[62%_center]" />
      <div className="absolute inset-0 bg-[linear-gradient(145deg,rgba(4,20,37,0.96),rgba(7,56,85,0.78)_55%,rgba(8,155,206,0.6))]" />
      <div className="absolute -right-20 top-24 size-72 rounded-full bg-brand-teal/30 blur-3xl" />
      <div className="relative z-10 flex items-center justify-between">
        <Link href="/" aria-label="CLOUT home"><Image src="/clout-logo.png" alt="CLOUT" width={128} height={32} className="h-8 w-auto" /></Link>
        <ThemeToggle className="border-white/25 bg-white/10 text-white hover:bg-white/20" />
      </div>
      <div className="relative z-10 my-auto max-w-xl pb-10 pt-24">
        <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3 py-1.5 text-xs font-medium tracking-wide backdrop-blur"><BadgeCheck className="size-4 text-brand-teal" /> THE CREATOR COMMERCE PLATFORM</p>
        <h1 className="text-5xl font-semibold tracking-tight text-balance">The work behind great influence, made simple.</h1>
        <p className="mt-5 max-w-lg text-lg leading-8 text-white/85">Find the right campaign, create scroll-stopping content, and turn genuine community attention into impact.</p>
      </div>
      <div className="relative z-10 grid gap-3 xl:grid-cols-3">
        {HIGHLIGHTS.map(({ icon: Icon, title, body }) => <div key={title} className="rounded-2xl border border-white/20 bg-brand-navy/55 p-4 backdrop-blur-md"><Icon className="size-5 text-brand-teal" /><p className="mt-3 text-sm font-semibold">{title}</p><p className="mt-1 text-xs leading-5 text-white/75">{body}</p></div>)}
      </div>
    </section>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const { user, access_token } = await login(email, password);
      setSession(user, access_token);
      router.push(`/${user.user_type}/dashboard`);
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail?: string }>;
      setError(axiosErr.response?.data?.detail ?? "We could not sign you in. Check your details and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950 lg:flex">
      <BrandStory />
      <section className="relative flex min-h-screen flex-1 items-center justify-center overflow-hidden px-5 py-10 sm:px-8">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-[radial-gradient(circle_at_top,rgba(14,165,233,0.13),transparent_64%)]" />
        <div className="relative z-10 w-full max-w-md">
          <div className="mb-8 flex items-center justify-between"><BackButton fallbackHref="/" className="-ml-2" /><Link href="/" className="lg:hidden"><Image src="/clout-logo.png" alt="CLOUT" width={112} height={28} className="h-7 w-auto" /></Link><ThemeToggle /></div>
          <div className="rounded-3xl border bg-background p-6 shadow-xl shadow-slate-950/10 sm:p-8 dark:shadow-black/30">
            <div className="mb-7"><div className="mb-4 flex size-11 items-center justify-center rounded-2xl bg-brand-teal/15 text-brand-teal"><LockKeyhole className="size-5" /></div><h2 className="text-2xl font-semibold tracking-tight">Welcome back</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">Sign in to manage your campaigns, content, and community.</p></div>
            <ContinueWithGoogleButton label="Continue with Google" className="h-11 rounded-xl" />
            <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground"><span className="h-px flex-1 bg-border" />or use email<span className="h-px flex-1 bg-border" /></div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2"><Label htmlFor="email">Email address</Label><Input id="email" type="email" placeholder="you@example.com" required value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" className="h-11 rounded-xl" /></div>
              <div className="space-y-2"><div className="flex items-center justify-between"><Label htmlFor="password">Password</Label><Link href="/forgot-password" className="text-xs font-medium text-brand-teal hover:underline">Forgot password?</Link></div><Input id="password" type="password" required value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" className="h-11 rounded-xl" /></div>
              {error && <p role="alert" className="rounded-xl border border-destructive/25 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
              <Button type="submit" className="h-11 w-full gap-2 rounded-xl" disabled={isSubmitting}>{isSubmitting ? "Signing in..." : <>Sign in <ArrowRight className="size-4" /></>}</Button>
            </form>
            <p className="mt-6 text-center text-sm text-muted-foreground">New to CLOUT? <Link href="/register" className="font-semibold text-foreground hover:text-brand-teal">Create your account</Link></p>
          </div>
          <p className="mt-5 text-center text-xs leading-5 text-muted-foreground">Your account is protected with secure authentication and privacy controls.</p>
        </div>
      </section>
    </main>
  );
}
