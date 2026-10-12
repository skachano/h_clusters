// A small "wiki" marker after a term or heading, opening the page that explains it.
// With children, the children themselves become the link instead.
import type { ReactNode } from "react";
import { useLang } from "../i18n";
import { wikiUrl, type WikiPage } from "../lib/wiki";

export function WikiLink({ page, anchor, children }: { page: WikiPage; anchor?: string; children?: ReactNode }) {
  const { lang, t } = useLang();
  const href = wikiUrl(page, lang, anchor);
  if (children) return <a href={href} title={t("wiki.title")}>{children}</a>;
  return (
    <a className="wiki-link" href={href} title={t("wiki.title")}>
      {t("wiki.marker")}
    </a>
  );
}
