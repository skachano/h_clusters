// View 2: one state — structure, isomers, spin states, fragmentation channels, properties.
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { jobFileUrl, useModes, useStateDetail, type StateDetail } from "../api/client";
import { ConditionsBar, Segmented } from "../components/ConditionsBar";
import { MoleculeViewer } from "../components/MoleculeViewer";
import { DivergingBars } from "../components/charts/DivergingBars";
import { LevelDiagram } from "../components/charts/LevelDiagram";
import { useConditions } from "../lib/conditions";
import { fmt, multiplicityName, pretty, signed, species } from "../lib/format";
import { VERDICT_FILL, VERDICT_INK, VERDICT_LABEL } from "../lib/scales";

type ChannelQ = "d_e" | "d_0" | "d_g";

export function SpeciesView() {
  const params = useParams();
  const campaign = params.campaign ?? "baseline";
  const [m, charge, mult] = [Number(params.m), Number(params.charge), Number(params.mult)];
  const { conditions, update, search } = useConditions();
  const detail = useStateDetail(campaign, m, charge, mult, conditions);
  const s = detail.data;
  const back = `/c/${campaign}${search ? `?${search}` : ""}`;

  return (
    <div className="stack">
      <div>
        <Link to={back}>← Grid</Link>
        <div className="row" style={{ alignItems: "baseline", gap: 12, marginTop: 6 }}>
          <h1>{species(m, charge)} <span className="secondary" style={{ fontWeight: 400 }}>{multiplicityName(mult)}</span></h1>
          {s && (
            <span className="badge" style={{ background: VERDICT_FILL[s.verdict], color: VERDICT_INK[s.verdict], border: "1px solid var(--border)" }}>
              {VERDICT_LABEL[s.verdict]}
            </span>
          )}
        </div>
        {s && s.multiplicities.length > 1 && (
          <nav className="nav" aria-label="Spin states" style={{ marginTop: 8 }}>
            {s.multiplicities.map((x) => (
              <Link key={x.mult} className={x.mult === mult ? "active" : ""}
                to={`/c/${campaign}/s/${m}/${charge}/${x.mult}${search ? `?${search}` : ""}`}>
                2S+1 = {x.mult} · {VERDICT_LABEL[x.verdict]}
              </Link>
            ))}
          </nav>
        )}
      </div>
      <ConditionsBar conditions={conditions} update={update} />
      {detail.isError && <p className="error">Could not load this state: {String(detail.error)}</p>}
      {detail.isPending && <p className="loading">Loading…</p>}
      {s && <Detail s={s} stale={detail.isPlaceholderData} />}
    </div>
  );
}

function Detail({ s, stale }: { s: StateDetail; stale: boolean }) {
  const [structureId, setStructureId] = useState<number | null>(s.structure_id ?? null);
  useEffect(() => setStructureId(s.structure_id ?? null), [s.structure_id]);
  const isomer = s.isomers.find((i) => i.structure_id === structureId) ?? s.isomers[0];
  const xyz = useQuery({
    queryKey: ["xyz", structureId],
    enabled: structureId != null && structureId !== s.structure_id,
    queryFn: async () => (await fetch(`/api/structures/${structureId}.xyz`)).text(),
  });
  const shownXyz = structureId === s.structure_id ? s.xyz : xyz.data;
  const modes = useModes(structureId);
  const [modeIndex, setModeIndex] = useState<number | null>(null);
  useEffect(() => setModeIndex(null), [structureId]);
  const mode = modeIndex != null && modes.data ? modes.data.modes[modeIndex] : null;

  if (!s.structure_id) return <NoStructure s={s} />;

  return (
    <div className={`stack ${stale ? "stale" : ""}`}>
      <div className="cols-2">
        <div className="card stack" style={{ gap: 10 }}>
          <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
            <h2>Structure</h2>
            <span className="secondary">
              {isomer?.point_group} · {isomer?.shape} · units {isomer?.composition} · optimized at {isomer?.geometry_level === "L1M" ? "RI-MP2" : "ωB97X-D4"}
            </span>
          </div>
          {shownXyz && <MoleculeViewer xyz={shownXyz} mode={mode} label={`3D structure of ${pretty(s.label)}`} />}
          {modes.data && (
            <div className="control">
              <label htmlFor="mode">Animate a normal mode (cm⁻¹, at {modes.data.level === "L1M" ? "RI-MP2" : "ωB97X-D4"})</label>
              <select id="mode" value={modeIndex ?? ""} onChange={(e) => setModeIndex(e.target.value === "" ? null : Number(e.target.value))}>
                <option value="">none</option>
                {modes.data.frequencies.map((f, i) => (
                  <option key={i} value={i}>{f < 0 ? `${Math.abs(f).toFixed(0)}i (imaginary)` : f.toFixed(0)}</option>
                ))}
              </select>
            </div>
          )}
        </div>
        <Properties s={s} />
      </div>

      <div className="cols-2">
        <Channels s={s} />
        <div className="card stack" style={{ gap: 10 }}>
          <h2>Isomers and spin states</h2>
          <div className="row" style={{ gap: 24 }}>
            <div style={{ flex: "1 1 260px" }}>
              <h3>Isomers</h3>
              <table>
                <thead><tr><th className="num">ΔE (eV)</th><th>Units</th><th>Point group</th><th>Geometry</th><th><span className="sr-only">View</span></th></tr></thead>
                <tbody>
                  {distinctIsomers(s.isomers).map(({ isomer: i, count }) => {
                    const selected = i.structure_id === (isomer?.structure_id ?? null);
                    return (
                      <tr key={i.structure_id} aria-selected={selected} style={selected ? { background: "var(--surface-2)" } : undefined}>
                        <td className="num">{i.relative.toFixed(3)}</td>
                        <td>{i.composition}{count > 1 && <span className="muted"> ×{count}</span>}</td>
                        <td>{i.point_group}</td>
                        <td>{i.geometry_level === "L1M" ? "RI-MP2" : "ωB97X-D4"}</td>
                        <td>
                          {selected ? <span className="muted">shown</span> : (
                            <button type="button" className="link-button" onClick={() => setStructureId(i.structure_id)}>view</button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="hint">CCSD(T) energy above the best structure; ×n: the same structure reached n times.</p>
            </div>
            <div style={{ flex: "1 1 220px" }}>
              <h3>Spin states (eV)</h3>
              {s.multiplicities.some((x) => x.spin_gap != null) ? (
                <LevelDiagram
                  ariaLabel="Spin-state energies"
                  unit="eV"
                  levels={s.multiplicities.filter((x) => x.spin_gap != null).map((x) => ({
                    key: String(x.mult), label: `2S+1 = ${x.mult}`, value: x.spin_gap as number, selected: x.mult === s.mult,
                  }))}
                />
              ) : <p className="muted">Only this spin state has a reference energy.</p>}
              {s.multiplicities.filter((x) => x.spin_gap == null).map((x) => (
                <p className="hint" key={x.mult}>2S+1 = {x.mult}: {VERDICT_LABEL[x.verdict]} (no energy to compare)</p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

type Isomer = StateDetail["isomers"][number];

/** Identical structures reached along several paths (same level, units, symmetry, energy). */
function distinctIsomers(isomers: Isomer[]): { isomer: Isomer; count: number }[] {
  const groups = new Map<string, { isomer: Isomer; count: number }>();
  for (const i of isomers) {
    const key = `${i.geometry_level}|${i.composition}|${i.point_group}|${i.energy.toFixed(6)}`;
    const g = groups.get(key);
    if (g) g.count += 1;
    else groups.set(key, { isomer: i, count: 1 });
  }
  return [...groups.values()];
}

function Channels({ s }: { s: StateDetail }) {
  const [q, setQ] = useState<ChannelQ>("d_e");
  const bars = s.channels.map((c) => ({ key: c.split, label: c.split, sublabel: c.limit !== c.split ? c.limit : undefined, value: c[q] ?? null }));
  const weakest = [...bars].filter((b) => b.value != null).sort((a, b) => (a.value as number) - (b.value as number))[0];
  return (
    <div className="card stack" style={{ gap: 10 }}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <h2>Ways to fall apart</h2>
          <p className="hint">Energy each spin-allowed channel costs; the weakest one decides. → shows where it ends up.</p>
        </div>
        <Segmented<ChannelQ> label="Energy" value={q} onChange={setQ}
          options={[{ value: "d_e", label: "D_e" }, { value: "d_0", label: "D₀" }, { value: "d_g", label: "D_G" }]} />
      </div>
      {bars.length ? <DivergingBars bars={bars} unit="eV" highlight={weakest?.key} /> : <p className="muted">No channels: an atom.</p>}
    </div>
  );
}

function Properties({ s }: { s: StateDetail }) {
  const rows: [string, string][] = [
    ["D_e (weakest channel)", `${signed(s.d_e, 3, "eV")}${s.channel ? ` → ${pretty(s.channel)}` : ""}`],
    ["D₀ (with zero-point energy)", signed(s.d_0, 3, "eV")],
    [`D_H at ${s.temperature.toFixed(0)} K`, signed(s.d_h, 3, "eV")],
    [`D_G at ${s.temperature.toFixed(0)} K, ${s.pressure.toPrecision(3)} atm`, `${signed(s.d_g, 3, "eV")}${s.channel_g && s.channel_g !== s.channel ? ` → ${pretty(s.channel_g)}` : ""}`],
    ...(s.charge === -1 ? [["Detachment (adiabatic)", signed(s.detachment, 3, "eV")] as [string, string]] : []),
    ...(s.charge === 0 ? [["Ionization (adiabatic)", signed(s.ionization, 3, "eV")] as [string, string]] : []),
    ["HOMO / LUMO (HF)", `${fmt(s.homo, 2)} / ${fmt(s.lumo, 2)} eV`],
    ["⟨S²⟩", s.s2 == null ? "–" : `${s.s2.toFixed(3)}${s.spin_contaminated ? " (spin-contaminated)" : ""}`],
    ["Point group · shape", `${s.point_group ?? "–"} · ${s.shape ?? "–"}`],
    ["Radius of gyration", fmt(s.radius_of_gyration, 2, "Å")],
    ["Energy, CCSD(T)/aVTZ", fmt(s.energy, 6, "Eh")],
    ["Zero-point energy", fmt(s.zpe == null ? null : s.zpe * 27.211386, 3, "eV")],
  ];
  const ref = s.isomers[0];
  return (
    <div className="card stack" style={{ gap: 10 }}>
      <h2>Properties</h2>
      <table>
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}><th scope="row" style={{ fontWeight: 400 }}>{k}</th><td className="num" style={{ textAlign: "right" }}>{v}</td></tr>
          ))}
        </tbody>
      </table>
      {ref && (
        <p className="hint">
          Raw ORCA files of the CCSD(T) job:{" "}
          <a href={jobFileUrl(ref.ref_job_id, "job.inp")} target="_blank" rel="noreferrer">input</a> ·{" "}
          <a href={jobFileUrl(ref.ref_job_id, "job.out")} target="_blank" rel="noreferrer">output</a> ·{" "}
          <a href={`/api/jobs/${ref.ref_job_id}`} target="_blank" rel="noreferrer">job record</a>
        </p>
      )}
    </div>
  );
}

function NoStructure({ s }: { s: StateDetail }) {
  const why = useMemo(() => ({
    unbound_electron: "The anion cannot hold its extra electron: at every level its highest occupied orbital lies above zero, so the electron sits in the most diffuse basis functions. There is no structure to show.",
    not_a_minimum: "Every structure found still had imaginary frequencies after three displacements: no true minimum.",
    dissociates: "Every optimization fell apart into fragments more than 3.5 Å apart.",
    atom: "A single atom: nothing to fall apart into.",
  } as Record<string, string>)[s.verdict] ?? "No reference energy.", [s.verdict]);
  return (
    <div className="card">
      <h2>No stable structure</h2>
      <p className="lede">{why}</p>
    </div>
  );
}
