"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { promoteToAdmin } from "@/lib/admin-api";
import { useAuthStore } from "@/store/auth-store";
import type { Page, User, UserType } from "@/types/auth";

const PAGE_SIZE = 10;

async function fetchUsers(page: number, userType: UserType | "all"): Promise<Page<User>> {
  const { data } = await api.get<Page<User>>("/admin/users", {
    params: {
      page,
      page_size: PAGE_SIZE,
      ...(userType !== "all" ? { user_type: userType } : {}),
    },
  });
  return data;
}

async function verifyEntity(user: User, status: "approved" | "rejected") {
  const path = user.user_type === "brand" ? `/admin/brands/${user.id}/verify` : `/admin/influencers/${user.id}/verify`;
  await api.patch(path, { status });
}

function UsersTable() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [userType, setUserType] = useState<UserType | "all">("all");
  const isSuperAdmin = useAuthStore((s) => s.user?.roles.includes("super_admin") ?? false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin", "users", page, userType],
    queryFn: () => fetchUsers(page, userType),
  });

  async function toggleActive(user: User) {
    await api.patch(`/admin/users/${user.id}/status`, { is_active: !user.is_active });
    await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
  }

  async function handleVerify(user: User, status: "approved" | "rejected") {
    await verifyEntity(user, status);
    await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
  }

  async function handlePromote(user: User) {
    const confirmed = window.confirm(
      `Make ${user.email} an admin? They will immediately lose access to their ${user.user_type} dashboard and gain full admin access instead.`,
    );
    if (!confirmed) return;
    await promoteToAdmin(user.id);
    await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Users</CardTitle>
        <Select
          value={userType}
          onValueChange={(v) => {
            setUserType(v as UserType | "all");
            setPage(1);
          }}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            <SelectItem value="brand">Brands</SelectItem>
            <SelectItem value="influencer">Influencers</SelectItem>
            <SelectItem value="admin">Admins</SelectItem>
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent>
        {isLoading && <p className="text-sm text-muted-foreground">Loading users...</p>}
        {error && <p className="text-sm text-destructive">Could not load users.</p>}
        {data && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.email}</TableCell>
                    <TableCell className="capitalize">{user.user_type}</TableCell>
                    <TableCell>
                      <Badge variant={user.is_active ? "default" : "destructive"}>
                        {user.is_active ? "Active" : "Suspended"}
                      </Badge>
                    </TableCell>
                    <TableCell className="flex justify-end gap-2">
                      {user.user_type !== "admin" && (
                        <>
                          <Button size="sm" variant="outline" onClick={() => handleVerify(user, "approved")}>
                            Verify
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => handleVerify(user, "rejected")}>
                            Reject
                          </Button>
                        </>
                      )}
                      <Button size="sm" variant="secondary" onClick={() => toggleActive(user)}>
                        {user.is_active ? "Suspend" : "Reactivate"}
                      </Button>
                      {isSuperAdmin && user.user_type !== "admin" && (
                        <Button size="sm" variant="outline" onClick={() => handlePromote(user)}>
                          Make admin
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Page {data.page} of {Math.max(1, Math.ceil(data.total / data.page_size))} ({data.total} users)
              </span>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page * data.page_size >= data.total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function AdminDashboardPage() {
  return (
    <RequireUserType allow={["admin"]}>
      <DashboardShell title="Admin overview">
        <div className="space-y-6">
          <UsersTable />
          <Card>
            <CardHeader>
              <CardTitle>Payments</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Manually settle a claimed slot's escrowed budget until Phase 6 automates verified-view-based
                settlement.
              </p>
              <Button size="sm" render={<Link href="/admin/settlement" />}>
                Slot settlement tool
              </Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Media review</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Brand-uploaded video, photo, and audio waits for approval here before it's broadcast to every
                influencer.
              </p>
              <Button size="sm" render={<Link href="/admin/media-review" />}>
                Review queue
              </Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Contracts</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Read-only oversight of every digital agreement between brands and influencers.
              </p>
              <Button size="sm" render={<Link href="/admin/contracts" />}>
                View contracts
              </Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Activity log</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Every audited action across the platform — role changes, verification decisions, payments,
                moderation calls — in one place.
              </p>
              <Button size="sm" render={<Link href="/admin/activity-logs" />}>
                View activity log
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardShell>
    </RequireUserType>
  );
}
