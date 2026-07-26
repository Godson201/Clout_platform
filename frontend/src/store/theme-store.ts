import { create } from "zustand";

export type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  /** Syncs store state from the DOM (already set by ThemeInitScript) without
   * touching the DOM/localStorage again — call once on mount. */
  hydrate: () => void;
  setTheme: (theme: Theme) => void;
  toggle: () => void;
}

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("clout-theme", theme);
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: "light",
  hydrate: () => {
    const current = document.documentElement.classList.contains("dark") ? "dark" : "light";
    set({ theme: current });
  },
  setTheme: (theme) => {
    applyTheme(theme);
    set({ theme });
  },
  toggle: () => {
    const next: Theme = get().theme === "dark" ? "light" : "dark";
    applyTheme(next);
    set({ theme: next });
  },
}));
