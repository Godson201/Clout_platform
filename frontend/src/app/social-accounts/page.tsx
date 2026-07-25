"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { disconnectSocialAccount, getConnectUrl, listMySocialAccounts } from "@/lib/social-api";
import { useAuthStore } from "@/store/auth-store";
import type { SocialAccountStatus } from "@/types/social";

const PLATFORMS = ["tiktok", "instagram", "facebook", "youtube"] as const;

function statusVariant(status: SocialAccountStatus) {
  if (status === "active") return "default" as const;
  if (status === "disconnected" || status === "revoked") return "destructive" as const;
  return "secondary" as const;
}

function SocialAccountsManager() {
  const queryClient = useQueryClient();
  const { data: accounts, isLoading } = useQuery({
    queryKey: ["social-accounts", "me"],
    queryFn: listMySocialAccounts,
  });

  const connectMutation = useMutation({
    mutationFn: (platform: string) => getConnectUrl(platform),
    onSuccess: (url) => {
      window.location.href = url;
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: (id: string) => disconnectSocialAccount(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["social-accounts", "me"] }),
  });

  const byPlatform = new Map((accounts ?? []).map((a) => [a.platform, a]));

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {PLATFORMS.map((platform) => {
        const account = byPlatform.get(platform);
        const connected = account && account.status === "active";

        return (
          <Card key={platform}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="capitalize">{platform}</CardTitle>
              {account && (
                <Badge variant={statusVariant(account.status)} className="capitalize">
                  {account.status}
                </Badge>
              )}
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              {account ? <p>@{account.handle}</p> : <p>Not connected</p>}
              {connected ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => disconnectMutation.mutate(account.id)}
                  disabled={disconnectMutation.isPending}
                >
                  Disconnect
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={() => connectMutation.mutate(platform)}
                  disabled={connectMutation.isPending}
                >
                  Connect
                </Button>
              )}
            </CardContent>
          </Card>
        );
      })}
      {isLoading && <p className="text-sm text-muted-foreground">Loading connected accounts...</p>}
    </div>
  );
}

export default function SocialAccountsPage() {
  const userType = useAuthStore((s) => s.user?.user_type);
  return (
    <RequireUserType allow={["brand", "influencer"]}>
      <DashboardShell title="Connected accounts">
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Connect TikTok, Instagram, Facebook, or YouTube to post campaign ads directly and track performance.
            Auto-posting and metrics only work on platforms CLOUT has been granted real API access for — everywhere
            else, posting falls back to a manual/assisted flow where you publish yourself and submit the post's URL.
          </p>
          <SocialAccountsManager />
          {userType === "influencer" && (
            <p className="text-xs text-muted-foreground">
              Once connected, use a claimed slot's page to post your campaign ad with this account.
            </p>
          )}
        </div>
      </DashboardShell>
    </RequireUserType>
  );
}
