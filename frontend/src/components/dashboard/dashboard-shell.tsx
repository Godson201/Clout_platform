"use client";

import { useQuery } from "@tanstack/react-query";
import { Bell, FileSignature, LogOut, MessageCircle, Search, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { BackButton } from "@/components/ui/back-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { listAnnouncements } from "@/lib/announcements-api";
import { logout as logoutRequest, resendVerificationEmail } from "@/lib/auth-api";
import { listConversations } from "@/lib/messaging-api";
import { useAuthStore } from "@/store/auth-store";

function initials(email: string) {
  return email.slice(0, 2).toUpperCase();
}

function UnverifiedEmailBanner() {
  const [status, setStatus] = useState<"idle" | "sending" | "sent">("idle");

  async function handleResend() {
    setStatus("sending");
    try {
      await resendVerificationEmail();
    } finally {
      setStatus("sent");
    }
  }

  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-warning/30 bg-warning/10 px-4 py-2 text-sm text-warning">
      <span>Please confirm your email address — check your inbox for a confirmation link.</span>
      {status === "sent" ? (
        <span className="text-xs font-medium">Sent — check your inbox.</span>
      ) : (
        <Button size="xs" variant="outline" onClick={handleResend} disabled={status === "sending"}>
          {status === "sending" ? "Sending..." : "Resend email"}
        </Button>
      )}
    </div>
  );
}

function NavIconLink({
  href,
  icon: Icon,
  label,
  badgeCount,
  isActive,
}: {
  href: string;
  icon: typeof MessageCircle;
  label: string;
  badgeCount?: number;
  isActive: boolean;
}) {
  return (
    <Button
      size="icon-sm"
      variant="outline"
      className={
        isActive
          ? "relative border-sidebar-primary bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary/90"
          : "relative border-white/15 bg-transparent text-sidebar-foreground hover:bg-white/10"
      }
      render={<Link href={href} title={label} />}
    >
      <Icon className="size-4" />
      {!!badgeCount && (
        <span className="absolute -top-1.5 -right-1.5 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
          {badgeCount > 9 ? "9+" : badgeCount}
        </span>
      )}
    </Button>
  );
}

function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  return (
    <form
      className="relative hidden md:block"
      onSubmit={(e) => {
        e.preventDefault();
        if (query.trim()) router.push(`/messages?q=${encodeURIComponent(query.trim())}`);
      }}
    >
      <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-white/50" />
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search conversations..."
        className="h-8 w-48 border-white/15 bg-white/5 pl-8 text-white placeholder:text-white/50 focus-visible:border-sidebar-primary lg:w-64"
      />
    </form>
  );
}

function NotificationCenter({ unreadCount }: { unreadCount: number }) {
  const { data: announcements } = useQuery({
    queryKey: ["announcements", "notification-center"],
    queryFn: listAnnouncements,
    refetchInterval: 60_000,
  });
  const latest = announcements?.slice(0, 4) ?? [];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <button type="button" className="relative outline-none">
            <span className="flex size-8 items-center justify-center rounded-lg border border-white/15 bg-transparent text-sidebar-foreground transition-colors hover:bg-white/10">
              <Bell className="size-4" />
            </span>
            {unreadCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>
        }
      />
      <DropdownMenuContent align="end" sideOffset={8} className="w-80">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Notifications</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {latest.length === 0 && <p className="px-1.5 py-2 text-sm text-muted-foreground">Nothing new right now.</p>}
          {latest.map((a) => (
            <DropdownMenuItem key={a.id} render={<Link href="/announcements" />} className="flex-col items-start gap-0.5">
              <span className="text-sm font-medium">{a.title}</span>
              <span className="line-clamp-2 text-xs text-muted-foreground">{a.body}</span>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem render={<Link href="/announcements" />}>View all announcements</DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function DashboardShell({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const clearSession = useAuthStore((s) => s.clearSession);
  const canMessage = user?.user_type === "brand" || user?.user_type === "influencer";

  const { data: conversations } = useQuery({
    queryKey: ["conversations", "unread-badge"],
    queryFn: listConversations,
    enabled: canMessage,
    refetchInterval: 15_000,
  });
  const unreadCount = conversations?.reduce((sum, c) => sum + c.unread_count, 0) ?? 0;

  async function handleLogout() {
    try {
      await logoutRequest();
    } finally {
      clearSession();
      router.push("/login");
    }
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b border-sidebar-border bg-sidebar text-sidebar-foreground">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-3">
            <img src="/clout-logo.png" alt="CLOUT" className="h-8 w-auto" />
            <Badge variant="outline" className="border-sidebar-border bg-sidebar-accent/20 capitalize text-sidebar-foreground">
              {user?.user_type}
            </Badge>
          </div>
          {canMessage && <SearchBar />}
          <div className="flex items-center gap-2">
            {canMessage && (
              <>
                <NavIconLink
                  href="/messages"
                  icon={MessageCircle}
                  label="Messages"
                  badgeCount={unreadCount}
                  isActive={pathname?.startsWith("/messages") ?? false}
                />
                <NavIconLink
                  href="/contracts"
                  icon={FileSignature}
                  label="Contracts"
                  isActive={pathname?.startsWith("/contracts") ?? false}
                />
              </>
            )}
            <NotificationCenter unreadCount={unreadCount} />
            <ThemeToggle className="border-white/15 bg-transparent text-sidebar-foreground hover:bg-white/10" />
            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <button type="button" className="ml-1 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <Avatar>
                      <AvatarFallback className="bg-sidebar-accent/20 text-sidebar-foreground">
                        {user ? initials(user.email) : "?"}
                      </AvatarFallback>
                    </Avatar>
                  </button>
                }
              />
              <DropdownMenuContent align="end" sideOffset={8}>
                <DropdownMenuGroup>
                  <DropdownMenuLabel>{user?.email}</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem render={<Link href="/settings" />}>
                    <Settings /> Account settings
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem variant="destructive" onClick={handleLogout}>
                    <LogOut /> Log out
                  </DropdownMenuItem>
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-4">
          <BackButton fallbackHref={user ? `/${user.user_type}/dashboard` : "/"} className="-ml-2" />
        </div>
        {user && !user.is_verified && <UnverifiedEmailBanner />}
        <h1 className="mb-6 text-2xl font-semibold">{title}</h1>
        <div className="animate-fade-in">{children}</div>
      </main>
    </div>
  );
}
