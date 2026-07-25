import { create } from "zustand";

import type { User } from "@/types/auth";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  /** True until the initial silent-refresh-on-load attempt has finished. */
  isBootstrapping: boolean;
  setSession: (user: User, accessToken: string) => void;
  clearSession: () => void;
  finishBootstrapping: () => void;
}

// accessToken is deliberately never persisted to localStorage/sessionStorage —
// it lives only in memory so an XSS payload can't read it off disk. The refresh
// token is an httpOnly cookie the browser holds, invisible to JS entirely.
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  isBootstrapping: true,
  setSession: (user, accessToken) => set({ user, accessToken }),
  clearSession: () => set({ user: null, accessToken: null }),
  finishBootstrapping: () => set({ isBootstrapping: false }),
}));
