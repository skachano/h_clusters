import { lazy, Suspense, useEffect, useState } from "react";
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { useCampaigns } from "./api/client";
import { BenchmarkView } from "./views/BenchmarkView";
import { GridView } from "./views/GridView";
import { JobsView } from "./views/JobsView";
import { StudiesView } from "./views/StudiesView";
import { TrendsView } from "./views/TrendsView";

// 3Dmol.js is most of the bundle and only the species page needs it.
const SpeciesView = lazy(() => import("./views/SpeciesView").then((m) => ({ default: m.SpeciesView })));

type Theme = "light" | "dark" | null;

function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      const t = localStorage.getItem("theme");
      return t === "light" || t === "dark" ? t : null;
    } catch {
      return null;
    }
  });
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
  return [theme, setTheme];
}

function Shell() {
  const { campaign = "baseline" } = useParams();
  const campaigns = useCampaigns();
  const navigate = useNavigate();
  const location = useLocation();
  const [theme, setTheme] = useTheme();
  const keep = location.search; // T, p, quantity follow you between views
  const link = (path: string) => `/c/${campaign}${path}${keep}`;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">H-clusters <span>· high-throughput study of H<sub>m</sub><sup>n</sup></span></div>
        <nav className="nav" aria-label="Views">
          <NavLink end to={link("")}>Grid</NavLink>
          <NavLink to={link("/trends")}>Trends</NavLink>
          <NavLink to={link("/benchmark")}>Benchmark</NavLink>
          <NavLink to={link("/studies")}>Extensions</NavLink>
          <NavLink to={link("/jobs")}>Jobs</NavLink>
        </nav>
        <div className="spacer" />
        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          <label className="secondary" htmlFor="campaign" style={{ fontSize: 12 }}>Campaign</label>
          <select id="campaign" value={campaign} onChange={(e) => navigate(`/c/${e.target.value}${keep}`)}>
            {(campaigns.data ?? [{ name: campaign, n_states: 0, n_jobs: 0 }]).map((c) => (
              <option key={c.name} value={c.name}>{c.name}{c.n_states ? ` (${c.n_states} states)` : ""}</option>
            ))}
          </select>
        </span>
        <button type="button" className="segmented" style={{ padding: "5px 10px", background: "transparent", cursor: "pointer" }}
          onClick={() => setTheme(theme === "dark" ? "light" : theme === "light" ? null : "dark")}
          title="Theme: follows the system unless set">
          {theme === null ? "Theme: auto" : theme === "dark" ? "Theme: dark" : "Theme: light"}
        </button>
      </header>
      <main>
        <Routes>
          <Route index element={<GridView />} />
          <Route path="s/:m/:charge/:mult" element={<Suspense fallback={<p className="loading">Loading…</p>}><SpeciesView /></Suspense>} />
          <Route path="trends" element={<TrendsView />} />
          <Route path="benchmark" element={<BenchmarkView />} />
          <Route path="studies" element={<StudiesView />} />
          <Route path="jobs" element={<JobsView />} />
        </Routes>
      </main>
      <footer className="site-footer secondary">
        Computed with ORCA 6.1.1 (F. Neese, <i>WIREs Comput. Mol. Sci.</i> 2025, 15, e70019,{" "}
        <a href="https://doi.org/10.1002/wcms.70019">doi:10.1002/wcms.70019</a>) · 3D view: 3Dmol.js (N. Rego,
        D. Koes, <i>Bioinformatics</i> 2015, 31, 1322,{" "}
        <a href="https://doi.org/10.1093/bioinformatics/btu829">doi:10.1093/bioinformatics/btu829</a>) · code
        under the MIT licence
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
