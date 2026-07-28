"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listAllContractsAdmin } from "@/lib/contracts-api";
import type { AdminContract, Contract } from "@/types/contract";

function statusVariant(status: Contract["status"]) {
  if (status === "accepted") return "success" as const;
  if (status === "declined" || status === "cancelled") return "destructive" as const;
  return "warning" as const;
}

function ContractCard({ contract }: { contract: AdminContract }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-sm">{contract.title}</CardTitle>
          <p className="text-xs text-muted-foreground">
            {contract.brand_name} ↔ @{contract.influencer_username}
          </p>
        </div>
        <Badge variant={statusVariant(contract.status)} className="capitalize">
          {contract.status}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-2">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-xs font-medium text-primary hover:underline"
        >
          {expanded ? "Hide terms" : "Open terms"}
        </button>
        {expanded && <p className="whitespace-pre-wrap text-sm text-muted-foreground">{contract.terms_text}</p>}
        <p className="text-xs text-muted-foreground">
          Proposed {new Date(contract.created_at).toLocaleDateString()}
          {contract.responded_at && ` · Responded ${new Date(contract.responded_at).toLocaleDateString()}`}
        </p>
      </CardContent>
    </Card>
  );
}

function ContractsList() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "contracts"],
    queryFn: listAllContractsAdmin,
  });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading...</p>;
  if (!data || data.length === 0) return <p className="text-sm text-muted-foreground">No contracts yet.</p>;

  return (
    <div className="space-y-4">
      {data.map((contract) => (
        <ContractCard key={contract.id} contract={contract} />
      ))}
    </div>
  );
}

export default function AdminContractsPage() {
  return (
    <RequireUserType allow={["admin"]}>
      <DashboardShell title="Contracts">
        <div className="space-y-6">
          <p className="text-sm text-muted-foreground">
            Read-only oversight of every digital agreement between brands and influencers — useful for dispute
            resolution. Accepting, declining, or cancelling stays exclusive to the two parties themselves.
          </p>
          <ContractsList />
        </div>
      </DashboardShell>
    </RequireUserType>
  );
}
