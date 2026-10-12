import { lazy, Suspense, useEffect } from "react";
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useCampaigns } from "./api/client";
import { useLang, type Lang } from "./i18n";
import { useTheme } from "./lib/themeChoice";
import { wikiUrl } from "./lib/wiki";

// Each language named in itself, so a reader who cannot read the current one finds theirs.
const LANGS: { code: Lang; label: string; name: string }[] = [
  { code: "en", label: "EN", name: "English" },
  { code: "ja", label: "JA", name: "日本語" },
];
import { BenchmarkView } from "./views/BenchmarkView";
import { GridView } from "./views/GridView";
import { JobsView } from "./views/JobsView";
import { StudiesView } from "./views/StudiesView";
import { TrendsView } from "./views/TrendsView";

// 3Dmol.js is most of the bundle and only the species page needs it.
const SpeciesView = lazy(() => import("./views/SpeciesView").then((m) => ({ default: m.SpeciesView })));

function Shell() {
  const { campaign = "baseline" } = useParams();
  const campaigns = useCampaigns();
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, setTheme } = useTheme();
  const { lang, setLang, t } = useLang();
  // Links from the wiki carry ?theme= (applied on load by ThemeProvider), and from the Japanese
  // wiki ?lang=ja: switch, then drop both from the address.
  const [params, setParams] = useSearchParams();
  const asked = params.get("lang");
  const linked = params.has("theme");
  useEffect(() => {
    if (asked === null && !linked) return;
    if (LANGS.some((l) => l.code === asked)) setLang(asked as Lang);
    setParams((p) => { p.delete("lang"); p.delete("theme"); return p; }, { replace: true });
  }, [asked, linked, setLang, setParams]);
  const keep = location.search; // T, p, quantity follow you between views
  const link = (path: string) => `/c/${campaign}${path}${keep}`;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">H-clusters <span>{t("app.brandBefore")}H<sub>m</sub><sup>n</sup>{t("app.brandAfter")}</span></div>
        <nav className="nav" aria-label={t("nav.aria")}>
          <NavLink end to={link("")}>{t("nav.grid")}</NavLink>
          <NavLink to={link("/trends")}>{t("nav.trends")}</NavLink>
          <NavLink to={link("/benchmark")}>{t("nav.benchmark")}</NavLink>
          <NavLink to={link("/studies")}>{t("nav.studies")}</NavLink>
          <NavLink to={link("/jobs")}>{t("nav.jobs")}</NavLink>
          <a href={wikiUrl("index", lang, { theme })} title={t("nav.wikiTitle")}>{t("nav.wiki")}</a>
        </nav>
        {/* One group: when the row is full, these move under the navigation together instead of
            leaving the last item (the language buttons) alone on a line of its own. */}
        <div className="topbar-tools">
          <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <label className="secondary" htmlFor="campaign" style={{ fontSize: 12 }}>{t("campaign.label")}</label>
            <select id="campaign" value={campaign} onChange={(e) => navigate(`/c/${e.target.value}${keep}`)}>
              {(campaigns.data ?? [{ name: campaign, n_states: 0, n_jobs: 0 }]).map((c) => (
                <option key={c.name} value={c.name}>{c.name}{c.n_states ? ` (${t("campaign.states", { n: c.n_states })})` : ""}</option>
              ))}
            </select>
          </span>
          <span className="topbar-pair">
            <button type="button" className="segmented" style={{ padding: "5px 10px", background: "transparent", cursor: "pointer" }}
              onClick={() => setTheme(theme === "dark" ? "light" : theme === "light" ? null : "dark")}
              title={t("theme.title")}>
              {theme === null ? t("theme.auto") : theme === "dark" ? t("theme.dark") : t("theme.light")}
            </button>
            <div className="segmented" role="group" aria-label={t("lang.title")}>
              {LANGS.map((l) => (
                <button key={l.code} type="button" lang={l.code} title={l.name} aria-pressed={lang === l.code}
                  onClick={() => setLang(l.code)}>
                  {l.label}
                </button>
              ))}
            </div>
          </span>
        </div>
      </header>
      <main>
        <Routes>
          <Route index element={<GridView />} />
          <Route path="s/:m/:charge/:mult" element={<Suspense fallback={<p className="loading">{t("common.loading")}</p>}><SpeciesView /></Suspense>} />
          <Route path="trends" element={<TrendsView />} />
          <Route path="benchmark" element={<BenchmarkView />} />
          <Route path="studies" element={<StudiesView />} />
          <Route path="jobs" element={<JobsView />} />
        </Routes>
      </main>
      <footer className="site-footer secondary">
        {t("footer.computed")} (F. Neese, <i>WIREs Comput. Mol. Sci.</i> 2025, 15, e70019,{" "}
        <a href="https://doi.org/10.1002/wcms.70019">doi:10.1002/wcms.70019</a>) · {t("footer.viewer")} (N. Rego,
        D. Koes, <i>Bioinformatics</i> 2015, 31, 1322,{" "}
        <a href="https://doi.org/10.1093/bioinformatics/btu829">doi:10.1093/bioinformatics/btu829</a>) ·{" "}
        {t("footer.licence")}
      </footer>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/c/baseline" replace />} />
      <Route path="/c/:campaign/*" element={<Shell />} />
      <Route path="*" element={<Navigate to="/c/baseline" replace />} />
    </Routes>
  );
}
