"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, CheckCircle2, CircleAlert, Link2, MessageSquareText, Send, Unplug } from "lucide-react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { disconnectSocialAccount, getConnectUrl, listMySocialAccounts, listSocialPlatformCapabilities } from "@/lib/social-api";
import { useAuthStore } from "@/store/auth-store";
import type { SocialAccountStatus } from "@/types/social";

const PLATFORMS = ["tiktok", "instagram", "facebook", "youtube"] as const;

const PLATFORM_COPY = {
  tiktok: "Short-form video and creator campaigns.",
  instagram: "Reels, visual stories, and brand partnerships.",
  facebook: "Community video and broad audience reach.",
  youtube: "Longer video, Shorts, and durable discovery.",
};

function statusVariant(status: SocialAccountStatus) {
  if (status === "active") return "success" as const;
  if (status === "expired") return "warning" as const;
  if (status === "disconnected" || status === "revoked") return "destructive" as const;
  return "secondary" as const;
}

function CapabilityLine({ enabled, label, icon: Icon }: { enabled: boolean; label: string; icon: typeof Send }) {
  return <li className={enabled ? "flex items-center gap-2 text-foreground" : "flex items-center gap-2 text-muted-foreground"}><Icon className={enabled ? "size-4 text-success" : "size-4"} />{label}{enabled && <CheckCircle2 className="ml-auto size-4 text-success" />}</li>;
}

function SocialAccountsManager() {
  const queryClient = useQueryClient();
  const { data: accounts, isLoading: accountsLoading } = useQuery({ queryKey: ["social-accounts", "me"], queryFn: listMySocialAccounts });
  const { data: capabilities, isLoading: capabilitiesLoading } = useQuery({ queryKey: ["social-accounts", "capabilities"], queryFn: listSocialPlatformCapabilities });
  const connectMutation = useMutation({ mutationFn: (platform: string) => getConnectUrl(platform), onSuccess: (url) => { window.location.href = url; } });
  const disconnectMutation = useMutation({ mutationFn: (id: string) => disconnectSocialAccount(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["social-accounts", "me"] }) });
  const byPlatform = new Map((accounts ?? []).map((account) => [account.platform, account]));
  const capabilitiesByPlatform = new Map((capabilities ?? []).map((capability) => [capability.platform, capability]));

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {PLATFORMS.map((platform) => {
        const account = byPlatform.get(platform);
        const capability = capabilitiesByPlatform.get(platform);
        const connected = account?.status === "active";
        const canAutoPublish = capability?.can_auto_publish ?? false;
        return (
          <Card key={platform} className="overflow-hidden">
            <CardHeader className="border-b bg-muted/25 pb-4">
              <div className="flex items-start justify-between gap-3"><div><CardTitle className="capitalize">{platform}</CardTitle><CardDescription className="mt-1">{PLATFORM_COPY[platform]}</CardDescription></div>{account ? <Badge variant={statusVariant(account.status)} className="capitalize">{account.status}</Badge> : <Badge variant="secondary">Not connected</Badge>}</div>
            </CardHeader>
            <CardContent className="space-y-4 pt-5">
              {connected ? <div className="rounded-lg border border-success/25 bg-success/5 px-3 py-2 text-sm"><span className="font-medium">@{account.handle}</span><span className="ml-2 text-muted-foreground">is connected</span></div> : <p className="text-sm text-muted-foreground">Connect the account you use to publish campaign content.</p>}
              <ul className="space-y-2 text-sm">
                <CapabilityLine enabled={canAutoPublish} label={canAutoPublish ? "Automatic publishing available" : "Manual or assisted publishing"} icon={Send} />
                <CapabilityLine enabled={capability?.can_fetch_metrics ?? false} label="Performance metrics" icon={BarChart3} />
                <CapabilityLine enabled={capability?.can_fetch_comments ?? false} label="Comment insights" icon={MessageSquareText} />
              </ul>
              {!canAutoPublish && <div className="flex gap-2 rounded-lg bg-muted/55 p-3 text-xs leading-5 text-muted-foreground"><CircleAlert className="mt-0.5 size-4 shrink-0" />CLOUT will never claim to auto-publish until this provider has approved the required API access. You can still connect your account and use the guided manual-posting flow.</div>}
              {connected ? <Button size="sm" variant="outline" onClick={() => disconnectMutation.mutate(account.id)} disabled={disconnectMutation.isPending}><Unplug className="size-4" />Disconnect</Button> : <Button size="sm" onClick={() => connectMutation.mutate(platform)} disabled={connectMutation.isPending}><Link2 className="size-4" />{connectMutation.isPending ? "Opening connection..." : `Connect ${platform}`}</Button>}
            </CardContent>
          </Card>
        );
      })}
      {(accountsLoading || capabilitiesLoading) && <p className="text-sm text-muted-foreground">Loading connection status...</p>}
      {connectMutation.isError && <p className="text-sm text-destructive">Could not start the connection. Please try again.</p>}
    </div>
  );
}

export default function SocialAccountsPage() {
  const userType = useAuthStore((state) => state.user?.user_type);
  return <RequireUserType allow={["brand", "influencer"]}><DashboardShell title="Connected accounts"><div className="mx-auto max-w-5xl space-y-6"><section><p className="text-sm font-semibold text-primary">PUBLISHING HUB</p><h1 className="mt-1 text-2xl font-bold tracking-tight">Connect the accounts behind your content</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">CLOUT shows exactly what each connection can do today. Connect an account once, then publish campaign content with a clear automatic or guided-manual path.</p></section><div className="grid gap-3 rounded-xl border bg-card p-4 sm:grid-cols-3"><p className="text-sm"><b className="block text-base">1. Connect</b><span className="text-muted-foreground">Authorize the account you own.</span></p><p className="text-sm"><b className="block text-base">2. Publish</b><span className="text-muted-foreground">Choose automatic or guided delivery.</span></p><p className="text-sm"><b className="block text-base">3. Track</b><span className="text-muted-foreground">See approved performance data.</span></p></div><SocialAccountsManager />{userType === "influencer" && <p className="rounded-xl border border-primary/15 bg-primary/5 p-4 text-sm text-muted-foreground">After connecting, open a claimed campaign slot to publish its approved creative. CLOUT will show the available delivery method before anything is sent.</p>}</div></DashboardShell></RequireUserType>;
}
