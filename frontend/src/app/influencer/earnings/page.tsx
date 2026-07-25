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
import { getMyInfluencerWallet, listPayouts, requestPayout } from "@/lib/payments-api";
import type { Payout } from "@/types/payment";

function payoutStatusVariant(status: Payout["status"]) {
  if (status === "successful") return "default" as const;
  if (status === "failed") return "destructive" as const;
  return "secondary" as const;
}

function WalletCard() {
  const queryClient = useQueryClient();
  const { data: wallet, isLoading } = useQuery({ queryKey: ["influencer", "wallet"], queryFn: getMyInfluencerWallet });
  const [amount, setAmount] = useState("");
  const [phone, setPhone] = useState("");

  const payoutMutation = useMutation({
    mutationFn: () => requestPayout(amount, phone),
    onSuccess: () => {
      setAmount("");
      queryClient.invalidateQueries({ queryKey: ["influencer", "wallet"] });
      queryClient.invalidateQueries({ queryKey: ["influencer", "payouts"] });
    },
  });

  const balance = wallet ? Number(wallet.balance) : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Wallet</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading balance...</p>
        ) : (
          <p className="text-2xl font-semibold">
            {balance.toLocaleString()} {wallet?.currency}
          </p>
        )}
        <p className="text-sm text-muted-foreground">
          Earnings are credited here once a brand's admin settles a completed slot. Withdraw to MTN MoMo minus the
          platform's payout fee.
        </p>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label htmlFor="payout-amount">Amount to withdraw</Label>
            <Input
              id="payout-amount"
              type="number"
              min="0"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={balance.toString()}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="payout-phone">MoMo phone number</Label>
            <Input id="payout-phone" placeholder="07XXXXXXXX" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
        </div>

        {payoutMutation.isError && (
          <p className="text-sm text-destructive">
            {(payoutMutation.error as AxiosError<{ detail?: string }>)?.response?.data?.detail ??
              "Something went wrong."}
          </p>
        )}

        <Button
          onClick={() => payoutMutation.mutate()}
          disabled={payoutMutation.isPending || !amount || !phone || balance <= 0}
        >
          {payoutMutation.isPending ? "Requesting..." : "Withdraw to MoMo"}
        </Button>
      </CardContent>
    </Card>
  );
}

function PayoutHistory() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["influencer", "payouts"],
    queryFn: () => listPayouts(),
    refetchInterval: 5000,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Payout history</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && <p className="text-sm text-muted-foreground">Loading payouts...</p>}
        {error && <p className="text-sm text-destructive">Could not load payout history.</p>}
        {data && data.items.length === 0 && (
          <p className="text-sm text-muted-foreground">No withdrawals yet.</p>
        )}
        {data && data.items.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Requested</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Fee</TableHead>
                <TableHead>Net (to MoMo)</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((payout) => (
                <TableRow key={payout.id}>
                  <TableCell>{new Date(payout.created_at).toLocaleString()}</TableCell>
                  <TableCell>
                    {Number(payout.amount).toLocaleString()} {payout.currency}
                  </TableCell>
                  <TableCell>{Number(payout.fee_amount).toLocaleString()}</TableCell>
                  <TableCell>{Number(payout.net_amount).toLocaleString()}</TableCell>
                  <TableCell>
                    <Badge variant={payoutStatusVariant(payout.status)} className="capitalize">
                      {payout.status}
                    </Badge>
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

export default function InfluencerEarningsPage() {
  return (
    <RequireUserType allow={["influencer"]}>
      <DashboardShell title="Earnings">
        <div className="space-y-6">
          <WalletCard />
          <PayoutHistory />
        </div>
      </DashboardShell>
    </RequireUserType>
  );
}
