"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { refreshAccessToken } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";

function AuthBootstrap({ children }: { children: React.ReactNode }) {
  const finishBootstrapping = useAuthStore((s) => s.finishBootstrapping);

  useEffect(() => {
    // The access token only ever lives in memory, so a hard page reload loses it.
    // Silently trade the httpOnly refresh cookie for a new one on first load.
    refreshAccessToken().finally(finishBootstrapping);
  }, [finishBootstrapping]);

  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            staleTime: 30_000,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthBootstrap>{children}</AuthBootstrap>
    </QueryClientProvider>
  );
}
