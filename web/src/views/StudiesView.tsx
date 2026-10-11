// Phase 8: extra calculations on the best structures, one table per study.
import { useParams } from "react-router-dom";
import { useStudies, useStudy } from "../api/client";
import { pretty } from "../lib/format";

interface StudyMeta {
  title: string;
  about: string;
  columns: Record<string, string>;
}

const STUDIES: Record<string, StudyMeta> = {
  vertical: {
    title: "Vertical vs adiabatic electron removal",
    about:
      "CCSD(T) of the species with one electron fewer at the same geometry (vertical) against the relaxed limit (adiabatic). VDE for anions, VIE for neutrals; the difference is how much the product relaxes.",
    columns: { state: "State", kind: "Kind", vertical_ev: "Vertical (eV)", adiabatic_ev: "Adiabatic (eV)", to_mult: "Final 2S+1", verdict: "Verdict" },
  },
  counterpoise: {
    title: "Counterpoise-corrected binding of the complexes",
    about:
      "Each fragment of the weakest channel borrows the others' basis functions inside the complex, which overbinds it. Removing that basis-set superposition error (BSSE) gives D_e(CP).",
    columns: { state: "State", channel: "Channel", d_e_ev: "D_e (eV)", bsse_ev: "BSSE (eV)", d_e_cp_ev: "D_e CP (eV)", d_0_cp_ev: "D₀ CP (eV)", bound_after_cp: "Bound after CP" },
  },
  anharmonic: {
    title: "Anharmonic zero-point energy (VPT2, RI-MP2)",
    about:
      "Quartic force field from Hessians at displaced geometries, then second-order vibrational perturbation theory. The last row corrects D₀ of H₅⁺ → H₃⁺ + H₂.",
    columns: { species: "Species", harmonic_cm: "Harmonic ZPE (cm⁻¹)", vpt2_cm: "VPT2 ZPE (cm⁻¹)", correction_cm: "Correction (cm⁻¹)", g0_cm: "G₀ (cm⁻¹)", rotation_cm: "Rotation (cm⁻¹)", frequencies_cm: "Harmonic ω (cm⁻¹)", harmonic_ev: "D₀ harmonic (eV)", vpt2_ev: "D₀ VPT2 (eV)" },
  },
  solvent: {
    title: "D_e in a dielectric continuum (CPCM, ωB97X-D4)",
    about:
      "Educational only: a dielectric rewards charge on small fragments, so ion–molecule complexes weaken as ε grows, while neutral complexes barely notice. The gas column is ωB97X-D4 and overbinds the H⁻ complexes (self-interaction error: 0.43 eV for H₃⁻ against 0.05 eV at CCSD(T)), so read the trend, not the numbers.",
    columns: { state: "State", channel: "Channel", gas: "Gas (eV)", eps2: "ε = 2", eps10: "ε = 10", eps80: "ε = 80" },
  },
  field: {
    title: "D_e in a static electric field (ωB97X-D4)",
    about:
      "Neutral clusters only (an ion would drift in a uniform field). Field along z in atomic units (0.01 a.u. = 0.51 V/Å); structures relax and may turn to align. D_e moves by at most ~3 meV even at 1 V/Å, about −½·Δα·F² with Δα the interaction-induced polarizability; shifts below ~1 meV at the weaker fields are within the precision of relaxing these floppy complexes.",
    columns: { state: "State", channel: "Channel", F0: "F = 0", "F0.005": "0.005", "F0.01": "0.01", "F0.02": "0.02", alpha_au: "α_zz (a.u.)" },
  },
  bonds: {
    title: "Bond orders (Löwdin, ωB97X-D4)",
    about:
      "Wiberg index in the Löwdin basis, spin density included, for the best structure of each state: about 1 inside an H₂ unit, 0.44 per side in H₃⁺, 0.2–0.35 for the links that hold ions together, and about 0.02 between van der Waals neighbours. Units are atoms closer than 1.15 Å. Every structure's full set is drawn in its 3D view.",
    columns: { state: "State", structure_id: "Structure", units: "Units", weakest_in_unit: "Weakest in a unit", strongest_in_unit: "Strongest in a unit", strongest_link: "Strongest link between units" },
  },
  basis: {
    title: "Basis-set limit and CCSD(T) geometries",
    about:
      "L4: CCSD(T) extrapolated from aVTZ and aVQZ to the complete basis set, D_e recomputed. L3: CCSD(T) geometry optimizations of H₂, H₃⁺ and both H₅⁺ structures.",
    columns: { item: "Item", channel: "Channel / geometry", avtz: "aVTZ / start", cbs: "CBS / CCSD(T) geometry", change: "Change", unit: "Units" },
  },
};

const ORDER = ["vertical", "counterpoise", "anharmonic", "basis", "bonds", "solvent", "field"];

export function StudiesView() {
  const { campaign = "baseline" } = useParams();
  const names = useStudies(campaign);
  const available = new Set(names.data ?? []);
  return (
    <div className="stack">
      <div>
        <h1>Extensions</h1>
        <p className="lede">
          Extra calculations on the campaign's best structures (Phase 8): what the main ladder leaves out,
          and how the answers move with basis set, anharmonicity and environment.
        </p>
      </div>
      {names.isError && <p className="error">{String(names.error)}</p>}
      {ORDER.filter((n) => available.has(n)).map((n) => <StudyCard key={n} campaign={campaign} name={n} />)}
      {[...available].filter((n) => !ORDER.includes(n)).map((n) => <StudyCard key={n} campaign={campaign} name={n} />)}
      {names.data && names.data.length === 0 && (
        <p className="muted">No study reports yet: run <code>python -m hclust study &lt;name&gt;</code>.</p>
      )}
    </div>
  );
}

function cell(value: unknown): string {
  if (value == null) return "–";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(Math.abs(value) >= 100 ? 1 : 4);
  if (Array.isArray(value)) return value.map(cell).join(", ");
  return pretty(String(value));
}

function StudyCard({ campaign, name }: { campaign: string; name: string }) {
  const study = useStudy(campaign, name);
  const meta = STUDIES[name] ?? { title: name, about: "", columns: {} };
  const rows = study.data?.rows ?? [];
  const keys = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  const columns = [...Object.keys(meta.columns).filter((k) => keys.includes(k)), ...keys.filter((k) => !(k in meta.columns))];
  return (
    <section className="card stack" style={{ gap: 8 }} aria-labelledby={`study-${name}`}>
      <h2 id={`study-${name}`}>{meta.title}</h2>
      {meta.about && <p className="hint" style={{ maxWidth: "80ch" }}>{meta.about}</p>}
      {study.isError && <p className="error">{String(study.error)}</p>}
      {rows.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>{columns.map((c) => <th key={c} className={typeof rows[0][c] === "number" ? "num" : undefined}>{meta.columns[c] ?? c}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  {columns.map((c) => <td key={c} className={typeof r[c] === "number" ? "num" : undefined}>{cell(r[c])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
