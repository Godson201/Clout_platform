"use client";

import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function BackButton({ fallbackHref = "/", className }: { fallbackHref?: string; className?: string }) {
  const router = useRouter();

  function handleBack() {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
    } else {
      router.push(fallbackHref);
    }
  }

  return (
    <Button variant="ghost" size="sm" onClick={handleBack} className={cn("gap-1.5", className)}>
      <ArrowLeft className="size-4" />
      Back
    </Button>
  );
}
