"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import type { AxiosError } from "axios";
import { BadgeCheck, BriefcaseBusiness, CheckCircle2, CircleUserRound, ShieldCheck } from "lucide-react";

import { ContinueWithGoogleButton } from "@/components/auth/continue-with-google-button";
import { AuthPageVisualBackground } from "@/components/marketing/auth-page-visual-background";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { BackButton } from "@/components/ui/back-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { emptyRwandaLocation, RwandaLocationPicker } from "@/components/location/rwanda-location-picker";
import { registerBrand, registerInfluencer } from "@/lib/auth-api";
import { SECURITY_QUESTIONS } from "@/lib/security-questions";
import { useAuthStore } from "@/store/auth-store";

function RegistrationBenefits() {
  return (
    <aside className="relative z-10 hidden w-[26rem] shrink-0 flex-col justify-between border-r border-white/15 bg-brand-navy/65 p-10 text-white backdrop-blur-sm xl:flex">
      <div>
        <Link href="/" aria-label="CLOUT home"><Image src="/clout-logo.png" alt="CLOUT" width={128} height={32} className="h-8 w-auto" /></Link>
        <p className="mt-20 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-semibold tracking-wide"><BadgeCheck className="size-4 text-brand-teal" /> START YOUR CLOUT JOURNEY</p>
        <h1 className="mt-5 text-4xl font-semibold leading-tight tracking-tight">Make partnerships that feel natural.</h1>
        <p className="mt-5 text-base leading-7 text-white/80">Set up your profile once, then discover the people, campaigns, and tools that fit your work.</p>
      </div>
      <div className="space-y-3">
        {["Use an email you already own", "Choose a brand or creator profile", "Build a trusted, verified presence"].map((benefit) => <p key={benefit} className="flex items-center gap-3 rounded-xl border border-white/15 bg-white/10 p-3 text-sm"><CheckCircle2 className="size-5 shrink-0 text-brand-teal" />{benefit}</p>)}
      </div>
    </aside>
  );
}

function useRegisterSubmit() {
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function run(fn: () => ReturnType<typeof registerBrand>) {
    setError(null);
    setIsSubmitting(true);
    try {
      const { user, access_token } = await fn();
      setSession(user, access_token);
      router.push(`/${user.user_type}/dashboard`);
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail?: string }>;
      setError(axiosErr.response?.data?.detail ?? "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return { run, error, isSubmitting };
}

interface SecurityState {
  security_question: string;
  security_answer: string;
}

function SecurityQuestionField({
  value,
  onChange,
  idPrefix,
}: {
  value: SecurityState;
  onChange: (patch: Partial<SecurityState>) => void;
  idPrefix: string;
}) {
  return (
    <div className="space-y-2 rounded-xl border bg-muted/20 p-3">
      <p className="flex items-start gap-2 text-xs leading-5 text-muted-foreground">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-brand-teal" /> Used to confirm it&apos;s really you if you ever need to reset your password.
      </p>
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}_security_question`}>Security question</Label>
        <Select value={value.security_question ?? ""} onValueChange={(v) => onChange({ security_question: v ?? "" })}>
          <SelectTrigger className="w-full" id={`${idPrefix}_security_question`}>
            <SelectValue placeholder="Choose a question" />
          </SelectTrigger>
          <SelectContent>
            {SECURITY_QUESTIONS.map((q) => (
              <SelectItem key={q} value={q}>
                {q}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}_security_answer`}>Your answer</Label>
        <Input
          id={`${idPrefix}_security_answer`}
          value={value.security_answer}
          onChange={(e) => onChange({ security_answer: e.target.value })}
          disabled={!value.security_question}
        />
      </div>
    </div>
  );
}

function PasswordFields({
  password,
  confirmPassword,
  onPasswordChange,
  onConfirmChange,
  idPrefix,
}: {
  password: string;
  confirmPassword: string;
  onPasswordChange: (v: string) => void;
  onConfirmChange: (v: string) => void;
  idPrefix: string;
}) {
  const mismatch = confirmPassword.length > 0 && password !== confirmPassword;
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}_password`}>Create a password</Label>
        <Input
          id={`${idPrefix}_password`}
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          value={password}
          onChange={(e) => onPasswordChange(e.target.value)}
        />
        <p className="text-xs text-muted-foreground">Use at least 8 characters.</p>
      </div>
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}_confirm_password`}>Confirm password</Label>
        <Input
          id={`${idPrefix}_confirm_password`}
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(e) => onConfirmChange(e.target.value)}
          aria-invalid={mismatch}
        />
        {mismatch && <p className="text-xs text-destructive">Passwords don&apos;t match.</p>}
      </div>
    </div>
  );
}

function BrandRegisterForm() {
  const { run, error, isSubmitting } = useRegisterSubmit();
  const [form, setForm] = useState({ email: "", password: "", confirm_password: "", business_name: "", sector: "" });
  const [location, setLocation] = useState(emptyRwandaLocation());
  const [security, setSecurity] = useState<SecurityState>({ security_question: "", security_answer: "" });

  const passwordsMatch = form.password === form.confirm_password;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!passwordsMatch) return;
        run(() =>
          registerBrand({
            email: form.email,
            password: form.password,
            business_name: form.business_name,
            sector: form.sector,
            ...location,
            ...(security.security_question ? security : {}),
          }),
        );
      }}
      className="space-y-4"
    >
      <ContinueWithGoogleButton userType="brand" label="Continue with Google" className="h-11 rounded-xl" />
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        or fill in manually
        <span className="h-px flex-1 bg-border" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="business_name">Business name</Label>
        <Input
          id="business_name"
          required
          value={form.business_name}
          onChange={(e) => setForm({ ...form, business_name: e.target.value })}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="brand_email">Work email address</Label>
        <Input
          id="brand_email"
          type="email"
          required
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          placeholder="you@yourbusiness.com"
        />
        <p className="text-xs text-muted-foreground">Use an email address your team can access.</p>
      </div>
      <PasswordFields
        idPrefix="brand"
        password={form.password}
        confirmPassword={form.confirm_password}
        onPasswordChange={(v) => setForm({ ...form, password: v })}
        onConfirmChange={(v) => setForm({ ...form, confirm_password: v })}
      />
      <div className="space-y-2">
        <Label htmlFor="sector">Industry / niche</Label>
        <Input
          id="sector"
          placeholder="e.g. beauty, retail, tech"
          value={form.sector}
          onChange={(e) => setForm({ ...form, sector: e.target.value })}
        />
      </div>
      <div className="space-y-2">
        <Label>Business location</Label>
        <RwandaLocationPicker value={location} onChange={(patch) => setLocation({ ...location, ...patch })} />
      </div>
      <SecurityQuestionField
        idPrefix="brand"
        value={security}
        onChange={(patch) => setSecurity({ ...security, ...patch })}
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" className="h-11 w-full rounded-xl" disabled={isSubmitting || !passwordsMatch}>
        {isSubmitting ? "Creating account..." : "Create brand account"}
      </Button>
    </form>
  );
}

function InfluencerRegisterForm() {
  const { run, error, isSubmitting } = useRegisterSubmit();
  const [form, setForm] = useState({
    email: "",
    password: "",
    confirm_password: "",
    display_name: "",
    username: "",
    sector: "",
  });
  const [location, setLocation] = useState(emptyRwandaLocation());
  const [security, setSecurity] = useState<SecurityState>({ security_question: "", security_answer: "" });

  const passwordsMatch = form.password === form.confirm_password;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!passwordsMatch) return;
        run(() =>
          registerInfluencer({
            email: form.email,
            password: form.password,
            display_name: form.display_name,
            username: form.username,
            sector: form.sector,
            ...location,
            ...(security.security_question ? security : {}),
          }),
        );
      }}
      className="space-y-4"
    >
      <ContinueWithGoogleButton userType="influencer" label="Continue with Google" className="h-11 rounded-xl" />
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        or fill in manually
        <span className="h-px flex-1 bg-border" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="display_name">Display name</Label>
          <Input
            id="display_name"
            required
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="username">Username</Label>
          <Input
            id="username"
            required
            pattern="[a-zA-Z0-9_.]+"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="inf_email">Email address</Label>
        <Input
          id="inf_email"
          type="email"
          required
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          placeholder="you@example.com"
        />
        <p className="text-xs text-muted-foreground">We&apos;ll use this to help protect and recover your account.</p>
      </div>
      <PasswordFields
        idPrefix="inf"
        password={form.password}
        confirmPassword={form.confirm_password}
        onPasswordChange={(v) => setForm({ ...form, password: v })}
        onConfirmChange={(v) => setForm({ ...form, confirm_password: v })}
      />
      <div className="space-y-2">
        <Label htmlFor="inf_sector">Niche</Label>
        <Input
          id="inf_sector"
          placeholder="e.g. beauty, lifestyle, tech"
          value={form.sector}
          onChange={(e) => setForm({ ...form, sector: e.target.value })}
        />
      </div>
      <div className="space-y-2">
        <Label>Location</Label>
        <RwandaLocationPicker value={location} onChange={(patch) => setLocation({ ...location, ...patch })} />
      </div>
      <SecurityQuestionField
        idPrefix="inf"
        value={security}
        onChange={(patch) => setSecurity({ ...security, ...patch })}
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" className="h-11 w-full rounded-xl" disabled={isSubmitting || !passwordsMatch}>
        {isSubmitting ? "Creating account..." : "Create influencer account"}
      </Button>
    </form>
  );
}

function RegisterTabs() {
  const searchParams = useSearchParams();
  const defaultTab = searchParams.get("type") === "influencer" ? "influencer" : "brand";

  return (
    <Tabs defaultValue={defaultTab}>
      <TabsList className="h-auto w-full rounded-xl bg-muted p-1">
        <TabsTrigger value="brand" className="flex flex-1 items-center gap-2 rounded-lg py-2.5">
          <BriefcaseBusiness className="size-4" /> I&apos;m a brand
        </TabsTrigger>
        <TabsTrigger value="influencer" className="flex flex-1 items-center gap-2 rounded-lg py-2.5">
          <CircleUserRound className="size-4" /> I&apos;m a creator
        </TabsTrigger>
      </TabsList>
      <TabsContent value="brand" className="mt-4">
        <BrandRegisterForm />
      </TabsContent>
      <TabsContent value="influencer" className="mt-4">
        <InfluencerRegisterForm />
      </TabsContent>
    </Tabs>
  );
}

export default function RegisterPage() {
  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-brand-navy xl:flex">
      <AuthPageVisualBackground />
      <RegistrationBenefits />
      <section className="relative z-10 flex min-h-screen flex-1 justify-center overflow-y-auto bg-slate-50/96 px-4 py-8 sm:px-8 xl:bg-background/95">
        <div className="w-full max-w-2xl">
          <div className="mb-7 flex items-center justify-between">
            <BackButton fallbackHref="/" className="-ml-2" />
            <Link href="/" className="xl:hidden"><Image src="/clout-logo.png" alt="CLOUT" width={112} height={28} className="h-7 w-auto" /></Link>
            <ThemeToggle />
          </div>
      <Card className="animate-fade-in rounded-3xl border shadow-xl shadow-slate-950/10 dark:shadow-black/30">
        <CardHeader className="border-b pb-5">
          <p className="text-xs font-semibold tracking-[0.16em] text-brand-teal">CREATE YOUR ACCOUNT</p>
          <CardTitle className="text-2xl">Join CLOUT</CardTitle>
          <CardDescription className="leading-6">Choose how you work. You can continue with Google or register securely with an email address you already use.</CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          <Suspense fallback={<p className="text-sm text-muted-foreground">Loading registration choices...</p>}>
            <RegisterTabs />
          </Suspense>
          <p className="mt-6 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="font-semibold text-foreground hover:text-brand-teal">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
          <p className="mt-5 text-center text-xs text-white/80 xl:text-muted-foreground">Admin accounts are created separately for platform security.</p>
        </div>
      </section>
    </main>
  );
}
