"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createAdvertisement, listTemplates } from "@/lib/advertisements-api";
import type { AdvertisementTemplate } from "@/types/advertisement";

function groupByCategory(templates: AdvertisementTemplate[]) {
  const groups = new Map<string, AdvertisementTemplate[]>();
  for (const template of templates) {
    const list = groups.get(template.category) ?? [];
    list.push(template);
    groups.set(template.category, list);
  }
  return groups;
}

function ToolkitContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<AdvertisementTemplate | null>(null);
  const [title, setTitle] = useState("");

  const { data: templates, isLoading } = useQuery({ queryKey: ["templates"], queryFn: listTemplates });

  const createMutation = useMutation({
    mutationFn: () => createAdvertisement({ template_id: selected!.id, title }),
    onSuccess: async (advertisement) => {
      await queryClient.invalidateQueries({ queryKey: ["advertisements"] });
      router.push(`/brand/ads/${advertisement.id}`);
    },
  });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading templates...</p>;

  if (selected) {
    return (
      <Card className="max-w-md">
        <CardHeader>
          <CardTitle>New ad from &quot;{selected.name}&quot;</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              createMutation.mutate();
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="ad-title">Title</Label>
              <Input id="ad-title" required value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <p className="text-sm text-muted-foreground">
              Default duration: {selected.default_duration_seconds}s. You can customize script, CTA, hashtags, and
              upload media in the editor next.
            </p>
            {createMutation.isError && <p className="text-sm text-destructive">Could not create advertisement.</p>}
            <div className="flex gap-2">
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create & continue"}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setSelected(null)}>
                Back
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    );
  }

  const groups = groupByCategory(templates ?? []);

  return (
    <div className="space-y-8">
      {[...groups.entries()].map(([category, categoryTemplates]) => (
        <div key={category}>
          <h2 className="mb-3 text-sm font-medium capitalize text-muted-foreground">{category}</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {categoryTemplates.map((template) => (
              <Card
                key={template.id}
                className="cursor-pointer transition-colors hover:border-primary"
                onClick={() => {
                  setSelected(template);
                  setTitle(`${template.name} — ${new Date().toLocaleDateString()}`);
                }}
              >
                <CardHeader>
                  <CardTitle className="text-base">{template.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {template.description ?? `~${template.default_duration_seconds}s short-form ad`}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function BrandToolkitPage() {
  return (
    <RequireUserType allow={["brand"]}>
      <DashboardShell title="Brand Toolkit">
        <ToolkitContent />
      </DashboardShell>
    </RequireUserType>
  );
}
