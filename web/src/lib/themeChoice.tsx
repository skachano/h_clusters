// The reader's theme choice: light, dark, or null to follow the system. Remembered in this
// browser, and carried across to the wiki and back as ?theme=light|dark|auto, because the two
// sites keep separate settings (and in development run on different origins).
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Theme = "light" | "dark" | null;

/** The theme as the ?theme= parameter writes it. */
export const themeParam = (theme: Theme) => theme ?? "auto";

export function parseTheme(value: string | null): Theme | undefined {
  return value === "light" || value === "dark" ? value : value === "auto" ? null : undefined;
}

/** ?theme= from a wiki link: in the query, or in the hash's query on the static (hash-routed) site. */
function linkedTheme(): Theme | undefined {
  const hashQuery = location.hash.includes("?") ? location.hash.slice(location.hash.indexOf("?")) : "";
  return parseTheme(new URLSearchParams(location.search).get("theme") ?? new URLSearchParams(hashQuery).get("theme"));
}

function initialTheme(): Theme {
  const linked = linkedTheme();
  if (linked !== undefined) return linked;
  try {
    return parseTheme(localStorage.getItem("theme")) ?? null;
  } catch {
    return null;
  }
}

interface ThemeContext {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const Context = createContext<ThemeContext>({ theme: null, setTheme: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme;
    else delete document.documentElement.dataset.theme;
    try {
      if (theme) localStorage.setItem("theme", theme);
      else localStorage.removeItem("theme");
    } catch {
      /* private mode: the toggle still works for this visit */
    }
  }, [theme]);
  const value = useMemo(() => ({ theme, setTheme }), [theme]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export const useTheme = () => useContext(Context);
