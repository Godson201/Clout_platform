"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuthStore } from "@/store/auth-store";

export default function Home() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const isBootstrapping = useAuthStore((s) => s.isBootstrapping);

  useEffect(() => {
    if (isBootstrapping) return;
    router.replace(user ? `/${user.user_type}/dashboard` : "/login");
  }, [isBootstrapping, user, router]);

  return (
    <main className="flex min-h-screen flex-1 items-center justify-center text-sm text-muted-foreground">
      Loading...
    </main>
  );
}
