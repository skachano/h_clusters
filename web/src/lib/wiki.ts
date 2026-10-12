// Links into the learning wiki (wiki/pages). On GitHub Pages it is published next to the app,
// under <base>/wiki/; in development it is the docs service on port 8001. VITE_WIKI_URL
// overrides both. The wiki puts Japanese pages under ja/.
import { STATIC } from "../api/static";
import type { Lang } from "../i18n";

/** Every wiki page the app links to, as its path under wiki/pages without ".md".
 *  A test checks that each one exists in both languages. */
export const WIKI_PAGES = [
  "foundations/chemical-and-van-der-waals-bonds",
  "foundations/electrons-charges-and-bond-lengths",
  "foundations/spin-and-multiplicity",
  "foundations/units-language-or-physics",
  "htc/method-ladder",
  "htc/provenance",
  "htc/resource-budgeting",
  "htc/selection-barriers",
  "methods/basis-sets",
  "methods/coupled-cluster",
  "methods/dft",
  "methods/diffusion-monte-carlo",
  "methods/hartree-fock",
  "methods/mp2",
  "pitfalls/spin-contamination",
  "pitfalls/unbound-anions",
  "techniques/fragmentation",
  "techniques/frequencies",
  "techniques/ionization-and-electron-affinity",
  "techniques/point-groups",
  "techniques/structure-search",
  "techniques/thermochemistry",
  "techniques/transition-states",
  "techniques/zero-point-energy",
] as const;
export type WikiPage = (typeof WIKI_PAGES)[number] | "index";

export function wikiBase(): string {
  const url = import.meta.env.VITE_WIKI_URL;
  if (url) return url.endsWith("/") ? url : `${url}/`;
  if (STATIC) return `${import.meta.env.BASE_URL}wiki/`;
  return `${location.protocol}//${location.hostname}:8001/`;
}

/** MkDocs serves page.md at page/ and section/index.md at section/. */
export function wikiUrl(page: WikiPage, lang: Lang, anchor?: string, base = wikiBase()): string {
  const path = page === "index" ? "" : `${page.replace(/(^|\/)index$/, "")}/`;
  return `${base}${lang === "en" ? "" : `${lang}/`}${path}${anchor ? `#${anchor}` : ""}`;
}
