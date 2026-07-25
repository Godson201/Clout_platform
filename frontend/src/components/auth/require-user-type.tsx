"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuthStore } from "@/store/auth-store";
import type { UserType } from "@/types/auth";

interface Props {
  allow: UserType[];
  children: React.ReactNode;
}

/** Gates a dashboard route to specific account types. Bootstrapping (the silent
 * refresh-on-load in `Providers`) must finish before we can trust `user` being
 * null actually means "not logged in" rather than "haven't checked yet".
 */
export function RequireUserType({ allow, children }: Props) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const isBootstrapping = useAuthStore((s) => s.isBootstrapping);

  useEffect(() => {
    if (isBootstrapping) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!allow.includes(user.user_type)) {
      router.replace(`/${user.user_type}/dashboard`);
    }
  }, [isBootstrapping, user, allow, router]);

  if (isBootstrapping || !user || !allow.includes(user.user_type)) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Loading...
      </div>
    );
  }

  return <>{children}</>;
}
