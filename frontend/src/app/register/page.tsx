"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import type { AxiosError } from "axios";

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
    <div className="space-y-2 rounded-lg border p-3">
      <p className="text-xs text-muted-foreground">
        Used to confirm it&apos;s really you if you ever need to reset your password.
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
    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}_password`}>Password</Label>
        <Input
          id={`${idPrefix}_password`}
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          value={password}
          onChange={(e) => onPasswordChange(e.target.value)}
        />
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
      <ContinueWithGoogleButton userType="brand" />
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
        <Label htmlFor="brand_email">Email</Label>
        <Input
          id="brand_email"
          type="email"
          required
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
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
      <Button type="submit" className="w-full" disabled={isSubmitting || !passwordsMatch}>
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
      <ContinueWithGoogleButton userType="influencer" />
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        or fill in manually
        <span className="h-px flex-1 bg-border" />
      </div>
      <div className="grid grid-cols-2 gap-4">
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
        <Label htmlFor="inf_email">Email</Label>
        <Input
          id="inf_email"
          type="email"
          required
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
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
      <Button type="submit" className="w-full" disabled={isSubmitting || !passwordsMatch}>
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
      <TabsList className="w-full">
        <TabsTrigger value="brand" className="flex-1">
          I&apos;m a brand
        </TabsTrigger>
        <TabsTrigger value="influencer" className="flex-1">
          I&apos;m an influencer
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
    <main className="relative isolate flex flex-1 flex-col items-center justify-center gap-4 p-4 py-12">
      <AuthPageVisualBackground />
      <div className="relative z-10 flex w-full max-w-2xl items-center justify-between">
        <BackButton fallbackHref="/" className="-ml-2 border-white/30 bg-transparent text-white hover:bg-white/10" />
        <ThemeToggle className="border-white/30 bg-transparent text-white hover:bg-white/10" />
      </div>
      {/* The form itself stays a solid (non-glass) card — this page carries a
          location picker, security-question dropdown, and several inputs, and
          translucency over a busy gradient would hurt legibility right where
          it matters most. Glass is reserved for lighter, marketing-style
          surfaces (hero panels, highlight chips). */}
      <Card className="relative z-10 w-full max-w-2xl animate-fade-in">
        <CardHeader>
          <CardTitle>Join CLOUT</CardTitle>
          <CardDescription>Admin accounts are provisioned separately and don&apos;t register here.</CardDescription>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<p className="text-sm text-muted-foreground">Loading...</p>}>
            <RegisterTabs />
          </Suspense>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="underline underline-offset-4">
              Log in
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
