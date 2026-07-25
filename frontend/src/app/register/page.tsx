"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { AxiosError } from "axios";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { registerBrand, registerInfluencer } from "@/lib/auth-api";
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

function BrandRegisterForm() {
  const { run, error, isSubmitting } = useRegisterSubmit();
  const [form, setForm] = useState({ email: "", password: "", business_name: "", sector: "", location: "" });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        run(() => registerBrand(form));
      }}
      className="space-y-4"
    >
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
      <div className="space-y-2">
        <Label htmlFor="brand_password">Password</Label>
        <Input
          id="brand_password"
          type="password"
          required
          minLength={8}
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="sector">Sector</Label>
          <Input id="sector" value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="location">Location</Label>
          <Input
            id="location"
            value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })}
          />
        </div>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" className="w-full" disabled={isSubmitting}>
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
    display_name: "",
    username: "",
    sector: "",
    location: "",
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        run(() => registerInfluencer(form));
      }}
      className="space-y-4"
    >
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
      <div className="space-y-2">
        <Label htmlFor="inf_password">Password</Label>
        <Input
          id="inf_password"
          type="password"
          required
          minLength={8}
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="inf_sector">Sector</Label>
          <Input
            id="inf_sector"
            value={form.sector}
            onChange={(e) => setForm({ ...form, sector: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="inf_location">Location</Label>
          <Input
            id="inf_location"
            value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })}
          />
        </div>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Creating account..." : "Create influencer account"}
      </Button>
    </form>
  );
}

export default function RegisterPage() {
  return (
    <main className="flex flex-1 items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Join CLOUT</CardTitle>
          <CardDescription>Admin accounts are provisioned separately and don&apos;t register here.</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="brand">
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
