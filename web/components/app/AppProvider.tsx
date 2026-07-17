"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

type Theme = "light" | "dark";
const STORAGE_KEY = "curso_ia_v3";

type AppState = {
  ready: boolean;
  theme: Theme;
  completed: Set<string>;
  isDone: (id: string) => boolean;
  doneCount: (ids: string[]) => number;
  toggleTheme: () => void;
  toggleComplete: (id: string) => void;
  reset: () => void;
  navOpen: boolean;
  toggleNav: () => void;
  closeNav: () => void;
};

const AppContext = createContext<AppState | null>(null);

function read(): { completed: string[]; theme?: Theme } {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return { completed: [] };
  }
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  // Render-neutral defaults first, then hydrate from localStorage in an effect
  // so SSR and the first client render match (no hydration mismatch).
  const [ready, setReady] = useState(false);
  const [theme, setThemeState] = useState<Theme>("light");
  const [completed, setCompleted] = useState<Set<string>>(new Set());
  const [navOpen, setNavOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const s = read();
    const stored = s.theme ?? (document.documentElement.getAttribute("data-theme") as Theme) ?? "light";
    setThemeState(stored);
    setCompleted(new Set(s.completed ?? []));
    setReady(true);
  }, []);

  // Close the mobile drawer whenever navigation lands on a new route.
  useEffect(() => {
    setNavOpen(false);
  }, [pathname]);

  // Close the drawer on Escape while it is open.
  useEffect(() => {
    if (!navOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setNavOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navOpen]);

  const persist = useCallback((next: { completed?: string[]; theme?: Theme }) => {
    const current = read();
    const merged = {
      completed: next.completed ?? current.completed ?? [],
      theme: next.theme ?? current.theme ?? theme,
    };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
    } catch {
      /* ignore quota / private mode */
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next: Theme = prev === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", next);
      persist({ theme: next });
      return next;
    });
  }, [persist]);

  const toggleComplete = useCallback((id: string) => {
    setCompleted((prev) => {
      const set = new Set(prev);
      set.has(id) ? set.delete(id) : set.add(id);
      persist({ completed: [...set] });
      return set;
    });
  }, [persist]);

  const reset = useCallback(() => {
    setCompleted(new Set());
    persist({ completed: [] });
  }, [persist]);

  const toggleNav = useCallback(() => setNavOpen((o) => !o), []);
  const closeNav = useCallback(() => setNavOpen(false), []);

  const value: AppState = {
    ready,
    theme,
    completed,
    isDone: (id) => completed.has(id),
    doneCount: (ids) => ids.reduce((n, id) => n + (completed.has(id) ? 1 : 0), 0),
    toggleTheme,
    toggleComplete,
    reset,
    navOpen,
    toggleNav,
    closeNav,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
