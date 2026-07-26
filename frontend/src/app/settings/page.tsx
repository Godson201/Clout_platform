"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { changePassword } from "@/lib/auth-api";
import { createHighlight, deleteHighlight, listMyHighlights } from "@/lib/profile-highlights-api";
import { useAuthStore } from "@/store/auth-store";
import type { Brand, Influencer, VisibilitySettings } from "@/types/auth";
import type { HighlightCategory, ProfileHighlight } from "@/types/profile-highlight";

const VISIBILITY_SECTIONS: { key: keyof VisibilitySettings; label: string; influencerOnly?: boolean }[] = [
  { key: "about", label: "Bio / description" },
  { key: "legacy", label: "My story / legacy" },
  { key: "location", label: "Location" },
  { key: "awards", label: "Awards" },
  { key: "events", label: "Events attended" },
  { key: "contact", label: "Contact info" },
  { key: "follower_stats", label: "Follower stats", influencerOnly: true },
];

function LegacyCard({ userType, initialLegacy }: { userType: "brand" | "influencer"; initialLegacy: string | null }) {
  const queryClient = useQueryClient();
  const [legacy, setLegacy] = useState(initialLegacy ?? "");
  const endpoint = userType === "brand" ? "/brands/me" : "/influencers/me";
  const queryKey = userType === "brand" ? ["brands", "me"] : ["influencers", "me"];

  const mutation = useMutation({
    mutationFn: () => api.patch(endpoint, { legacy }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your story</CardTitle>
        <CardDescription>Career highlights, milestones, or the lasting impact you want people to know about.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Textarea value={legacy} onChange={(e) => setLegacy(e.target.value)} rows={5} placeholder="Tell your story..." />
        <Button size="sm" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
          {mutation.isPending ? "Saving..." : "Save"}
        </Button>
      </CardContent>
    </Card>
  );
}

function HighlightForm({ category, onCreated }: { category: HighlightCategory; onCreated: () => void }) {
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [occurredOn, setOccurredOn] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      createHighlight({
        category,
        title,
        subtitle: subtitle || undefined,
        occurred_on: occurredOn || undefined,
      }),
    onSuccess: () => {
      setTitle("");
      setSubtitle("");
      setOccurredOn("");
      onCreated();
    },
  });

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
      <Input
        className="sm:col-span-2"
        placeholder={category === "award" ? "Award title" : "Event title"}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <Input
        placeholder={category === "award" ? "Issued by (optional)" : "Location (optional)"}
        value={subtitle}
        onChange={(e) => setSubtitle(e.target.value)}
      />
      <div className="flex gap-2">
        <Input type="date" value={occurredOn} onChange={(e) => setOccurredOn(e.target.value)} />
        <Button size="sm" onClick={() => mutation.mutate()} disabled={mutation.isPending || title.trim().length < 1}>
          Add
        </Button>
      </div>
    </div>
  );
}

function HighlightsCard({ highlights, category, title, description }: { highlights: ProfileHighlight[]; category: HighlightCategory; title: string; description: string }) {
  const queryClient = useQueryClient();
  const items = highlights.filter((h) => h.category === category);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteHighlight(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile-highlights", "me"] }),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {items.length === 0 && <p className="text-sm text-muted-foreground">Nothing added yet.</p>}
        <ul className="space-y-2">
          {items.map((h) => (
            <li key={h.id} className="flex items-center justify-between rounded-md border p-2 text-sm">
              <div>
                <p className="font-medium">{h.title}</p>
                <p className="text-xs text-muted-foreground">
                  {[h.subtitle, h.occurred_on].filter(Boolean).join(" · ") || "—"}
                </p>
              </div>
              <Button size="xs" variant="ghost" onClick={() => deleteMutation.mutate(h.id)} disabled={deleteMutation.isPending}>
                Remove
              </Button>
            </li>
          ))}
        </ul>
        <HighlightForm category={category} onCreated={() => queryClient.invalidateQueries({ queryKey: ["profile-highlights", "me"] })} />
      </CardContent>
    </Card>
  );
}

function VisibilityCard({
  userType,
  visibility,
}: {
  userType: "brand" | "influencer";
  visibility: VisibilitySettings;
}) {
  const queryClient = useQueryClient();
  const endpoint = userType === "brand" ? "/brands/me" : "/influencers/me";
  const queryKey = userType === "brand" ? ["brands", "me"] : ["influencers", "me"];

  const mutation = useMutation({
    mutationFn: (next: VisibilitySettings) => api.patch(endpoint, { visibility_settings: next }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  function toggle(key: keyof VisibilitySettings) {
    const current = visibility[key] ?? true;
    mutation.mutate({ ...visibility, [key]: !current });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile visibility</CardTitle>
        <CardDescription>Choose what other brands and influencers can see on your public profile.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {VISIBILITY_SECTIONS.filter((s) => !s.influencerOnly || userType === "influencer").map((section) => (
          <label key={section.key} className="flex items-center justify-between gap-3 text-sm">
            <span>{section.label}</span>
            <Checkbox checked={visibility[section.key] ?? true} onCheckedChange={() => toggle(section.key)} />
          </label>
        ))}
      </CardContent>
    </Card>
  );
}

function ChangePasswordCard() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: () => changePassword({ current_password: currentPassword, new_password: newPassword }),
    onSuccess: () => {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSuccess(true);
    },
  });

  const mismatch = confirmPassword.length > 0 && newPassword !== confirmPassword;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change password</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label>Current password</Label>
          <Input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>New password</Label>
            <Input type="password" minLength={8} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Confirm new password</Label>
            <Input
              type="password"
              minLength={8}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              aria-invalid={mismatch}
            />
            {mismatch && <p className="text-xs text-destructive">Passwords don&apos;t match.</p>}
          </div>
        </div>
        {mutation.isError && (
          <p className="text-sm text-destructive">
            {(mutation.error as AxiosError<{ detail?: string }>)?.response?.data?.detail ?? "Could not change your password."}
          </p>
        )}
        {success && <p className="text-sm text-success">Password updated.</p>}
        <Button
          size="sm"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !currentPassword || newPassword.length < 8 || mismatch}
        >
          {mutation.isPending ? "Updating..." : "Update password"}
        </Button>
      </CardContent>
    </Card>
  );
}

function SettingsApp() {
  const user = useAuthStore((s) => s.user);
  const isBrand = user?.user_type === "brand";

  const { data: brand } = useQuery({
    queryKey: ["brands", "me"],
    queryFn: async () => (await api.get<Brand>("/brands/me")).data,
    enabled: isBrand,
  });
  const { data: influencer } = useQuery({
    queryKey: ["influencers", "me"],
    queryFn: async () => (await api.get<Influencer>("/influencers/me")).data,
    enabled: !isBrand,
  });
  const { data: highlights } = useQuery({ queryKey: ["profile-highlights", "me"], queryFn: listMyHighlights });

  const profile = isBrand ? brand : influencer;
  if (!profile) return <p className="text-sm text-muted-foreground">Loading settings...</p>;

  return (
    <div className="space-y-6">
      <LegacyCard userType={isBrand ? "brand" : "influencer"} initialLegacy={profile.legacy} />
      <div className="grid gap-6 md:grid-cols-2">
        <HighlightsCard highlights={highlights ?? []} category="award" title="Awards" description="Recognitions you've received." />
        <HighlightsCard highlights={highlights ?? []} category="event" title="Events attended" description="Conferences, summits, or campaigns you were part of." />
      </div>
      <VisibilityCard userType={isBrand ? "brand" : "influencer"} visibility={profile.visibility_settings} />
      <ChangePasswordCard />
    </div>
  );
}

export default function SettingsPage() {
  return (
    <RequireUserType allow={["brand", "influencer"]}>
      <DashboardShell title="Account settings">
        <SettingsApp />
      </DashboardShell>
    </RequireUserType>
  );
}
