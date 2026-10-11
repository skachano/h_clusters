// UI language: English or Japanese. t(key, vars) looks the key up in the current language
// and fills {name} placeholders. The choice is remembered in this browser; the first visit
// follows the browser's language.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { en, type Key } from "./en";
import { ja } from "./ja";

export type Lang = "en" | "ja";
export type { Key };
export type T = (key: Key, vars?: Record<string, string | number>) => string;

const DICTIONARIES: Record<Lang, Record<Key, string>> = { en, ja };

export function translate(lang: Lang, key: Key, vars?: Record<string, string | number>): string {
  const text: string = DICTIONARIES[lang][key] ?? en[key];
  return vars ? text.replace(/\{(\w+)\}/g, (m, name: string) => (name in vars ? String(vars[name]) : m)) : text;
}

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem("lang");
    if (saved === "en" || saved === "ja") return saved;
  } catch {
    /* storage blocked: fall back to the browser language */
  }
  return globalThis.navigator?.language?.toLowerCase().startsWith("ja") ? "ja" : "en";
}

interface LangContext {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: T;
}

const Context = createContext<LangContext>({ lang: "en", setLang: () => {}, t: (key, vars) => translate("en", key, vars) });

export function LangProvider({ children, lang: fixed }: { children: ReactNode; lang?: Lang }) {
  const [lang, setLang] = useState<Lang>(() => fixed ?? initialLang());
  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem("lang", lang);
    } catch {
      /* private mode: the choice lasts for this visit */
    }
  }, [lang]);
  const t = useCallback<T>((key, vars) => translate(lang, key, vars), [lang]);
  const value = useMemo(() => ({ lang, setLang, t }), [lang, t]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export const useLang = () => useContext(Context);
export const useT = () => useContext(Context).t;
