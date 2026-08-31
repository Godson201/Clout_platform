"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  Clapperboard,
  FileSignature,
  Gauge,
  History,
  ImageIcon,
  ListChecks,
  LogOut,
  Megaphone,
  MessageCircle,
  Menu,
  PlusCircle,
  Scale,
  Search,
  Settings,
  Share2,
  Sparkles,
  Store,
  Wallet as WalletIcon,
  Wand2,
  X,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { BackButton } from "@/components/ui/back-button";
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
import { listNotifications, markAllNotificationsRead, markNotificationRead } from "@/lib/notifications-api";
import { getMyBrandWallet, getMyInfluencerWallet } from "@/lib/payments-api";
import { useAuthStore } from "@/store/auth-store";
import type { Notification } from "@/types/notification";
import type { UserType } from "@/types/auth";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: Record<UserType, NavItem[]> = {
  brand: [
    { href: "/brand/dashboard", label: "Overview", icon: Gauge },
    { href: "/social", label: "Clout Feed", icon: Sparkles },
    { href: "/brand/campaigns", label: "Campaigns", icon: Megaphone },
    { href: "/brand/campaigns/new", label: "Create Campaign", icon: PlusCircle },
    { href: "/brand/toolkit", label: "Ad Toolkit", icon: Wand2 },
    { href: "/brand/ads", label: "Ads Library", icon: Clapperboard },
    { href: "/messages", label: "Messages", icon: MessageCircle },
    { href: "/contracts", label: "Contracts", icon: FileSignature },
    { href: "/social-accounts", label: "Connected Accounts", icon: Share2 },
    { href: "/announcements", label: "Announcements", icon: Sparkles },
    { href: "/settings", label: "Settings", icon: Settings },
  ],
  influencer: [
    { href: "/influencer/dashboard", label: "Overview", icon: Gauge },
    { href: "/social", label: "Clout Feed", icon: Sparkles },
    { href: "/influencer/marketplace", label: "Marketplace", icon: Store },
    { href: "/influencer/slots", label: "My Slots", icon: ListChecks },
    { href: "/influencer/earnings", label: "Earnings", icon: WalletIcon },
    { href: "/messages", label: "Messages", icon: MessageCircle },
    { href: "/contracts", label: "Contracts", icon: FileSignature },
    { href: "/social-accounts", label: "Connected Accounts", icon: Share2 },
    { href: "/announcements", label: "Announcements", icon: Sparkles },
    { href: "/settings", label: "Settings", icon: Settings },
  ],
  admin: [
    { href: "/admin/dashboard", label: "Overview", icon: Gauge },
    { href: "/admin/media-review", label: "Media Review", icon: ImageIcon },
    { href: "/admin/contracts", label: "Contracts", icon: FileSignature },
    { href: "/admin/settlement", label: "Settlement", icon: Scale },
    { href: "/admin/activity-logs", label: "Activity Log", icon: History },
    { href: "/announcements", label: "Announcements", icon: Sparkles },
    { href: "/settings", label: "Settings", icon: Settings },
  ],
};

const DASHBOARD_LABEL: Record<UserType, string> = {
  brand: "Brand Dashboard",
  influencer: "Influencer Dashboard",
  admin: "Admin Dashboard",
};

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

function AccountBalanceCard({ userType }: { userType: UserType }) {
  const isBrand = userType === "brand";
  const isInfluencer = userType === "influencer";

  const { data: wallet } = useQuery({
    queryKey: ["wallet", userType],
    queryFn: isBrand ? getMyBrandWallet : getMyInfluencerWallet,
    enabled: isBrand || isInfluencer,
  });

  if (!isBrand && !isInfluencer) return null;

  return (
    <div className="rounded-xl border border-sidebar-border bg-sidebar-accent/40 p-3">
      <p className="text-xs text-sidebar-foreground/70">Account Balance</p>
      <div className="mt-1 flex items-center justify-between gap-2">
        <p className="truncate text-sm font-semibold text-sidebar-foreground">
          {wallet ? `${wallet.currency} ${Number(wallet.balance).toLocaleString()}` : "—"}
        </p>
        <Button
          size="icon-xs"
          className="shrink-0 rounded-full"
          render={<Link href={isBrand ? "/brand/campaigns/new" : "/influencer/earnings"} title="View details" />}
        >
          <PlusCircle className="size-3.5" />
        </Button>
      </div>
    </div>
  );
}

function SidebarNav({ items, pathname, onNavigate }: { items: NavItem[]; pathname: string | null; onNavigate?: () => void }) {
  return (
    <nav className="flex-1 space-y-0.5 px-3">
      {items.map(({ href, label, icon: Icon }) => {
        const isActive = pathname === href || (href !== "/" && pathname?.startsWith(href + "/")) || false;
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={
              isActive
                ? "flex items-center gap-2.5 rounded-lg bg-sidebar-primary px-3 py-2 text-sm font-medium text-sidebar-primary-foreground transition-colors"
                : "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-sidebar-foreground/80 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
            }
          >
            <Icon className="size-4 shrink-0" />
            <span className="truncate">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarContent({
  userType,
  pathname,
  onNavigate,
}: {
  userType: UserType;
  pathname: string | null;
  onNavigate?: () => void;
}) {
  return (
    <>
      <div className="flex items-center px-5 py-5">
        <img src="/clout-logo.png" alt="CLOUT" className="h-7 w-auto" />
      </div>
      <SidebarNav items={NAV_ITEMS[userType]} pathname={pathname} onNavigate={onNavigate} />
      <div className="p-3">
        <AccountBalanceCard userType={userType} />
      </div>
    </>
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
      <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search conversations..."
        className="h-8 w-48 pl-8 lg:w-64"
      />
    </form>
  );
}

function NotificationIcon({ type }: { type: Notification["type"] }) {
  if (type === "influencer_post_published") return <Megaphone className="size-4 text-primary" />;
  return <Sparkles className="size-4 text-primary" />;
}

function NotificationCenter({ messageUnreadCount }: { messageUnreadCount: number }) {
  const queryClient = useQueryClient();

  const { data: notifications } = useQuery({
    queryKey: ["notifications"],
    queryFn: listNotifications,
    refetchInterval: 20_000,
  });
  const { data: announcements } = useQuery({
    queryKey: ["announcements", "notification-center"],
    queryFn: listAnnouncements,
    refetchInterval: 60_000,
  });

  const latestNotifications = notifications?.slice(0, 5) ?? [];
  const latestAnnouncements = announcements?.slice(0, 3) ?? [];
  const notifUnreadCount = notifications?.filter((n) => !n.is_read).length ?? 0;
  const totalUnreadCount = messageUnreadCount + notifUnreadCount;

  async function handleOpenNotification(n: Notification) {
    if (!n.is_read) {
      await markNotificationRead(n.id);
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    }
  }

  async function handleMarkAllRead() {
    await markAllNotificationsRead();
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <button type="button" className="relative outline-none">
            <span className="flex size-8 items-center justify-center rounded-lg border border-border bg-transparent text-foreground transition-colors hover:bg-muted">
              <Bell className="size-4" />
            </span>
            {totalUnreadCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
                {totalUnreadCount > 9 ? "9+" : totalUnreadCount}
              </span>
            )}
          </button>
        }
      />
      <DropdownMenuContent align="end" sideOffset={8} className="w-80">
        <DropdownMenuGroup>
          <div className="flex items-center justify-between px-1.5">
            <DropdownMenuLabel className="px-0">Notifications</DropdownMenuLabel>
            {notifUnreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                className="text-xs font-medium text-primary hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>
          <DropdownMenuSeparator />
          {latestNotifications.length === 0 && (
            <p className="px-1.5 py-2 text-sm text-muted-foreground">Nothing new right now.</p>
          )}
          {latestNotifications.map((n) => (
            <DropdownMenuItem
              key={n.id}
              render={<Link href={n.link ?? "#"} />}
              onClick={() => handleOpenNotification(n)}
              className="flex-col items-start gap-0.5"
            >
              <span className="flex w-full items-center gap-1.5">
                <NotificationIcon type={n.type} />
                <span className="text-sm font-medium">{n.title}</span>
                {!n.is_read && <span className="ml-auto size-1.5 shrink-0 rounded-full bg-destructive" />}
              </span>
              <span className="line-clamp-2 text-xs text-muted-foreground">{n.body}</span>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuLabel className="px-1.5">Announcements</DropdownMenuLabel>
          {latestAnnouncements.length === 0 && (
            <p className="px-1.5 py-2 text-sm text-muted-foreground">No announcements right now.</p>
          )}
          {latestAnnouncements.map((a) => (
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
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

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
    <div className="flex min-h-screen bg-background">
      {user && (
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
          <SidebarContent userType={user.user_type} pathname={pathname} />
        </aside>
      )}

      {mobileNavOpen && user && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileNavOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex h-full w-72 flex-col bg-sidebar shadow-xl">
            <div className="flex items-center justify-end px-3 pt-3">
              <button
                type="button"
                onClick={() => setMobileNavOpen(false)}
                className="rounded-lg p-1.5 text-sidebar-foreground/70 hover:bg-sidebar-accent"
              >
                <X className="size-4" />
              </button>
            </div>
            <SidebarContent userType={user.user_type} pathname={pathname} onNavigate={() => setMobileNavOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-border bg-card px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileNavOpen(true)}
              className="rounded-lg p-1.5 text-foreground hover:bg-muted lg:hidden"
              aria-label="Open navigation menu"
            >
              <Menu className="size-5" />
            </button>
            <span className="truncate text-sm font-medium text-muted-foreground">
              {user ? DASHBOARD_LABEL[user.user_type] : "CLOUT"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {canMessage && <SearchBar />}
            <NotificationCenter messageUnreadCount={unreadCount} />
            <ThemeToggle />
            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <button type="button" className="ml-1 flex items-center gap-2 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <Avatar>
                      <AvatarFallback>{user ? initials(user.email) : "?"}</AvatarFallback>
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
        </header>
        <main className="flex-1 px-4 py-6 sm:px-6">
          <div className="mb-4">
            <BackButton fallbackHref={user ? `/${user.user_type}/dashboard` : "/"} className="-ml-2" />
          </div>
          {user && !user.is_verified && <UnverifiedEmailBanner />}
          <h1 className="mb-6 text-2xl font-semibold">{title}</h1>
          <div className="animate-fade-in">{children}</div>
        </main>
      </div>
    </div>
  );
}
