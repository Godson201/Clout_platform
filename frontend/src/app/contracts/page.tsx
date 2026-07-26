"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { acceptContract, cancelContract, declineContract, listContracts, proposeContract } from "@/lib/contracts-api";
import { useAuthStore } from "@/store/auth-store";
import type { Contract } from "@/types/contract";

function statusVariant(status: Contract["status"]) {
  if (status === "accepted") return "success" as const;
  if (status === "declined" || status === "cancelled") return "destructive" as const;
  return "warning" as const;
}

function NewContractForm({ counterpartId, counterpartName }: { counterpartId: string; counterpartName: string }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [terms, setTerms] = useState("");

  const mutation = useMutation({
    mutationFn: () => proposeContract({ counterpart_id: counterpartId, title, terms_text: terms }),
    onSuccess: () => {
      setTitle("");
      setTerms("");
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Propose a contract with {counterpartName}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Title</Label>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. TikTok campaign agreement" />
        </div>
        <div className="space-y-2">
          <Label>Terms</Label>
          <Textarea
            value={terms}
            onChange={(e) => setTerms(e.target.value)}
            rows={6}
            placeholder="Deliverables, timeline, payment terms, and any other agreed conditions..."
          />
        </div>
        {mutation.isError && (
          <p className="text-sm text-destructive">
            {(mutation.error as AxiosError<{ detail?: string }>)?.response?.data?.detail ?? "Could not propose this contract."}
          </p>
        )}
        <Button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || title.trim().length < 2 || terms.trim().length < 10}
        >
          {mutation.isPending ? "Sending..." : "Send for review"}
        </Button>
        <p className="text-xs text-muted-foreground">
          This is a lightweight digital agreement, not a legal e-signature — {counterpartName} will see the terms and
          can accept or decline, with a timestamped record either way.
        </p>
      </CardContent>
    </Card>
  );
}

function ContractCard({ contract }: { contract: Contract }) {
  const queryClient = useQueryClient();
  const userId = useAuthStore((s) => s.user?.id);
  const isProposer = contract.proposed_by_user_id === userId;

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["contracts"] });
  }

  const accept = useMutation({ mutationFn: () => acceptContract(contract.id), onSuccess: invalidate });
  const decline = useMutation({ mutationFn: () => declineContract(contract.id), onSuccess: invalidate });
  const cancel = useMutation({ mutationFn: () => cancelContract(contract.id), onSuccess: invalidate });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base">{contract.title}</CardTitle>
        <Badge variant={statusVariant(contract.status)} className="capitalize">
          {contract.status}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="whitespace-pre-wrap text-sm text-muted-foreground">{contract.terms_text}</p>
        <p className="text-xs text-muted-foreground">
          {isProposer ? "Proposed by you" : "Proposed to you"} on {new Date(contract.created_at).toLocaleDateString()}
          {contract.responded_at && ` · Responded ${new Date(contract.responded_at).toLocaleDateString()}`}
        </p>
        {contract.status === "proposed" && !isProposer && (
          <div className="flex gap-2">
            <Button size="sm" onClick={() => accept.mutate()} disabled={accept.isPending}>
              Accept
            </Button>
            <Button size="sm" variant="outline" onClick={() => decline.mutate()} disabled={decline.isPending}>
              Decline
            </Button>
          </div>
        )}
        {contract.status === "proposed" && isProposer && (
          <Button size="sm" variant="ghost" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
            Cancel proposal
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function ContractsApp() {
  const searchParams = useSearchParams();
  const withId = searchParams.get("with");
  const withName = searchParams.get("name");

  const { data: contracts, isLoading } = useQuery({ queryKey: ["contracts"], queryFn: listContracts });

  return (
    <div className="space-y-6">
      {withId && withName && <NewContractForm counterpartId={withId} counterpartName={withName} />}

      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground">Your contracts</h2>
        {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}
        {!isLoading && (!contracts || contracts.length === 0) && (
          <p className="text-sm text-muted-foreground">
            No contracts yet. Open a conversation with a brand or influencer you&apos;re working with and use
            &quot;Propose contract&quot; there.
          </p>
        )}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {contracts?.map((c) => <ContractCard key={c.id} contract={c} />)}
        </div>
      </div>
    </div>
  );
}

export default function ContractsPage() {
  return (
    <RequireUserType allow={["brand", "influencer"]}>
      <DashboardShell title="Contracts">
        <Suspense fallback={<p className="text-sm text-muted-foreground">Loading...</p>}>
          <ContractsApp />
        </Suspense>
      </DashboardShell>
    </RequireUserType>
  );
}
