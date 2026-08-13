"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listAuditLogs } from "@/lib/admin-api";
import type { AuditLog } from "@/types/audit";

function entityBadgeVariant(entityType: string) {
  if (entityType === "user") return "secondary" as const;
  if (entityType === "campaign") return "success" as const;
  return "outline" as const;
}

function ChangeDetail({ log }: { log: AuditLog }) {
  const [open, setOpen] = useState(false);
  if (!log.before && !log.after) return null;

  return (
    <div>
      <button type="button" onClick={() => setOpen((v) => !v)} className="text-xs text-primary hover:underline">
        {open ? "Hide details" : "View details"}
      </button>
      {open && (
        <pre className="mt-2 max-w-md overflow-x-auto rounded-md bg-muted p-2 text-[11px] whitespace-pre-wrap">
          {JSON.stringify({ before: log.before, after: log.after }, null, 2)}
        </pre>
      )}
    </div>
  );
}

function ActivityLogTable() {
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin", "audit-logs", page, actionFilter],
    queryFn: () => listAuditLogs(page, actionFilter || undefined),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Activity log</CardTitle>
        <Input
          value={actionFilter}
          onChange={(e) => {
            setActionFilter(e.target.value);
            setPage(1);
          }}
          placeholder="Filter by action (e.g. admin.user.status_update)"
          className="w-72"
        />
      </CardHeader>
      <CardContent>
        {isLoading && <p className="text-sm text-muted-foreground">Loading activity...</p>}
        {error && <p className="text-sm text-destructive">Could not load the activity log.</p>}
        {data && data.items.length === 0 && (
          <p className="text-sm text-muted-foreground">Nothing recorded yet.</p>
        )}
        {data && data.items.length > 0 && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                      {new Date(log.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm">{log.actor_email ?? "System"}</TableCell>
                    <TableCell>
                      <code className="text-xs">{log.action}</code>
                    </TableCell>
                    <TableCell>
                      <Badge variant={entityBadgeVariant(log.entity_type)} className="capitalize">
                        {log.entity_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <ChangeDetail log={log} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Page {data.page} of {Math.max(1, Math.ceil(data.total / data.page_size))} ({data.total} events)
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

export default function AdminActivityLogsPage() {
  return (
    <RequireUserType allow={["admin"]}>
      <DashboardShell title="Activity log">
        <ActivityLogTable />
      </DashboardShell>
    </RequireUserType>
  );
}
