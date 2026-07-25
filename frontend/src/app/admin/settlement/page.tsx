"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listAwaitingSettlement, settleSlot } from "@/lib/admin-api";
import type { CampaignSlot } from "@/types/campaign";

function slotStatusVariant(status: CampaignSlot["status"]) {
  if (status === "completed") return "default" as const;
  if (status === "failed" || status === "cancelled") return "destructive" as const;
  return "secondary" as const;
}

function AwaitingSettlementQueue({ onPick }: { onPick: (slotId: string) => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "awaiting-settlement"],
    queryFn: listAwaitingSettlement,
    refetchInterval: 15000,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Awaiting settlement ({data?.length ?? 0})</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-4 text-sm text-muted-foreground">
          Slots whose performance window has closed on a platform CLOUT can't verify metrics for automatically —
          every real platform today. Slots on platforms with real metrics access settle themselves on a schedule and
          never appear here.
        </p>
        {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}
        {data && data.length === 0 && <p className="text-sm text-muted-foreground">Nothing awaiting review.</p>}
        {data && data.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Brand</TableHead>
                <TableHead>Influencer</TableHead>
                <TableHead>Platform</TableHead>
                <TableHead>Post</TableHead>
                <TableHead>Window closed</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((item) => (
                <TableRow key={item.slot_id}>
                  <TableCell>{item.brand_name}</TableCell>
                  <TableCell>@{item.influencer_username}</TableCell>
                  <TableCell className="capitalize">{item.platform}</TableCell>
                  <TableCell>
                    {item.post_url ? (
                      <a href={item.post_url} target="_blank" rel="noreferrer" className="underline">
                        View
                      </a>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>{new Date(item.window_closed_at).toLocaleDateString()}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="outline" onClick={() => onPick(item.slot_id)}>
                      Review
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function SettlementTool({ slotId, setSlotId }: { slotId: string; setSlotId: (id: string) => void }) {
  const queryClient = useQueryClient();
  const [deliveredPct, setDeliveredPct] = useState("100");

  const mutation = useMutation({
    mutationFn: () => settleSlot(slotId, deliveredPct),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "awaiting-settlement"] }),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Manual slot settlement</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Enter what fraction of a slot's target was actually delivered, based on checking the post yourself — the
          corresponding share of its escrowed budget is released to the influencer immediately, and the remainder
          stays parked in the campaign's escrow until Phase 8's recovery engine decides what to do with it.
        </p>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div className="space-y-1">
            <Label htmlFor="slot-id">Slot ID</Label>
            <Input id="slot-id" value={slotId} onChange={(e) => setSlotId(e.target.value)} placeholder="UUID" />
          </div>
          <div className="space-y-1">
            <Label htmlFor="delivered-pct">Delivered %</Label>
            <Input
              id="delivered-pct"
              type="number"
              min="0"
              max="100"
              value={deliveredPct}
              onChange={(e) => setDeliveredPct(e.target.value)}
            />
          </div>
        </div>

        {mutation.isError && (
          <p className="text-sm text-destructive">
            {(mutation.error as AxiosError<{ detail?: string }>)?.response?.data?.detail ?? "Something went wrong."}
          </p>
        )}

        <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !slotId}>
          {mutation.isPending ? "Settling..." : "Settle slot"}
        </Button>

        {mutation.isSuccess && (
          <div className="rounded-md border p-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Result:</span>
              <Badge variant={slotStatusVariant(mutation.data.status)} className="capitalize">
                {mutation.data.status}
              </Badge>
            </div>
            <p className="mt-2 text-muted-foreground">
              Slot budget: {Number(mutation.data.budget_allocated).toLocaleString()}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SettlementPageContent() {
  const [slotId, setSlotId] = useState("");
  return (
    <div className="space-y-6">
      <AwaitingSettlementQueue onPick={setSlotId} />
      <SettlementTool slotId={slotId} setSlotId={setSlotId} />
    </div>
  );
}

export default function AdminSettlementPage() {
  return (
    <RequireUserType allow={["admin"]}>
      <DashboardShell title="Slot settlement">
        <SettlementPageContent />
      </DashboardShell>
    </RequireUserType>
  );
}
