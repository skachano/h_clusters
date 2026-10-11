// View 2: one state — structure, isomers, spin states, fragmentation channels, properties.
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, useBonds, useModes, useStateDetail, type BondsOut, type StateDetail } from "../api/client";
import { ConditionsBar, Segmented } from "../components/ConditionsBar";
import { MoleculeViewer } from "../components/MoleculeViewer";
import { RawFiles } from "../components/RawFiles";
import { DivergingBars } from "../components/charts/DivergingBars";
import { LevelDiagram } from "../components/charts/LevelDiagram";
import { useConditions } from "../lib/conditions";
import { fmt, multiplicityName, pretty, signed, species } from "../lib/format";
import { atomLabel, atomSummaries } from "../lib/atoms";
import { HALO_FULL, haloStyle, halos as haloList, type Highlight } from "../lib/halos";
import { bondStyle, MIN_BOND_ORDER, parseXyz } from "../lib/geometry";
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
    queryFn: async () => (await fetchApi(`/api/structures/${structureId}.xyz`)).text(),
  });
  const shownXyz = structureId === s.structure_id ? s.xyz : xyz.data;
  const modes = useModes(structureId);
  const [modeIndex, setModeIndex] = useState<number | null>(null);
  useEffect(() => setModeIndex(null), [structureId]);
  const mode = modeIndex != null && modes.data ? modes.data.modes[modeIndex] : null;
  const bonds = useBonds(structureId);
  const [bondView, setBondView] = useState<"order" | "distance">("order");
  const byOrder = bondView === "order" && bonds.data != null;
  const atoms = useMemo(() => (bonds.data ? atomSummaries(bonds.data) : null), [bonds.data]);
  const atomLabels = useMemo(() => atoms?.map(atomLabel) ?? null, [atoms]);
  const openShell = atoms?.some((a) => a.spin != null) ?? false;
  const [highlight, setHighlight] = useState<Highlight>("none");
  const shownHighlight: Highlight = highlight === "spin" && !openShell ? "none" : highlight;
  const halos = useMemo(
    () => (atoms && shownHighlight !== "none" ? haloList(atoms, shownHighlight) : null),
    [atoms, shownHighlight],
  );

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
          {shownXyz && (
            <MoleculeViewer xyz={shownXyz} mode={mode} bondOrders={byOrder ? bonds.data!.loewdin : null}
              atomLabels={atomLabels} halos={halos} label={`3D structure of ${pretty(s.label)}`} />
          )}
          {bonds.data && (
            <div className="row" style={{ justifyContent: "space-between", alignItems: "end", flexWrap: "wrap", gap: 10 }}>
              <Segmented label="Bonds" value={bondView} onChange={setBondView} options={[
                { value: "order", label: "by bond order", title: "Löwdin bond order sets thickness and opacity" },
                { value: "distance", label: "by distance", title: `H–H shorter than 1.15 Å` },
              ]} />
              {byOrder && <BondLegend animating={mode != null} />}
            </div>
          )}
          {atoms && (
            <div className="row" style={{ justifyContent: "space-between", alignItems: "end", flexWrap: "wrap", gap: 10 }}>
              <Segmented label="Highlight atoms" value={shownHighlight} onChange={setHighlight} options={[
                { value: "none", label: "none" },
                { value: "charge", label: "charge", title: "Löwdin atomic charge" },
                ...(openShell ? [{ value: "spin" as const, label: "spin", title: "Löwdin spin population: where the unpaired electrons sit" }] : []),
              ]} />
              {shownHighlight !== "none" && <HaloLegend kind={shownHighlight} animating={mode != null} />}
            </div>
          )}
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

      {bonds.data && atoms && shownXyz && (
        <div className="cols-2">
          <AtomTable atoms={atoms} method={bonds.data.method} />
          <BondTable bonds={bonds.data} xyz={shownXyz} />
        </div>
      )}

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
          Raw ORCA files of the CCSD(T) job: <RawFiles jobId={ref.ref_job_id} names={["job.inp", "job.out"]} record />
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


function BondLegend({ animating }: { animating: boolean }) {
  if (animating) return <span className="secondary">Bond orders return when the vibration stops.</span>;
  const samples = [0.25, 0.5, 0.75, 1];
  return (
    <figure className="row" style={{ gap: 8, alignItems: "center", margin: 0 }} aria-label="Bond order legend">
      <figcaption className="secondary">Löwdin bond order</figcaption>
      {samples.map((o) => {
        const st = bondStyle(o)!;
        return (
          <span key={o} className="row" style={{ gap: 4, alignItems: "center" }}>
            <svg width="28" height="12" aria-hidden="true">
              <line x1="2" y1="6" x2="26" y2="6" stroke="var(--text-primary)" strokeOpacity={st.opacity}
                strokeWidth={st.radius * 2 * 40} strokeLinecap="round" />
            </svg>
            <span className="secondary">{o}</span>
          </span>
        );
      })}
      <span className="secondary">· below {MIN_BOND_ORDER} not drawn</span>
    </figure>
  );
}

function BondTable({ bonds, xyz }: { bonds: BondsOut; xyz: string }) {
  const atoms = parseXyz(xyz);
  const mayer = new Map(bonds.mayer.map((b) => [`${b.i}-${b.j}`, b.order]));
  const rows = [...bonds.loewdin]
    .filter((b) => b.order >= MIN_BOND_ORDER || Math.abs(mayer.get(`${b.i}-${b.j}`) ?? 0) >= MIN_BOND_ORDER)
    .sort((a, b) => b.order - a.order);
  const distance = (i: number, j: number) =>
    Math.hypot(atoms[i].x - atoms[j].x, atoms[i].y - atoms[j].y, atoms[i].z - atoms[j].z);
  return (
    <details className="card">
      <summary><h2 style={{ display: "inline" }}>Bond orders</h2> <span className="secondary">({rows.length} {rows.length === 1 ? "contact" : "contacts"} ≥ {MIN_BOND_ORDER}, {bonds.method})</span></summary>
      <p className="secondary">
        How many electron pairs each H–H contact shares (Wiberg index in the Löwdin basis, spin density
        included): 1 for H₂, 0.5 for the one-electron bond of H₂⁺, 4/9 ≈ 0.44 on each side of H₃⁺ (two
        electrons over three bonds), and near 0 for van der Waals contacts. Mayer orders, from the same
        calculation, are noisier with this diffuse basis set and can dip below zero.
      </p>
      <table>
        <thead><tr><th>Atoms</th><th className="num">Distance (Å)</th><th className="num">Löwdin</th><th className="num">Mayer</th></tr></thead>
        <tbody>
          {rows.map((b) => (
            <tr key={`${b.i}-${b.j}`}>
              <td>H{b.i + 1}–H{b.j + 1}</td>
              <td className="num">{distance(b.i, b.j).toFixed(3)}</td>
              <td className="num">{b.order.toFixed(3)}</td>
              <td className="num">{mayer.has(`${b.i}-${b.j}`) ? mayer.get(`${b.i}-${b.j}`)!.toFixed(3) : "–"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}


function AtomTable({ atoms, method }: { atoms: ReturnType<typeof atomSummaries>; method: string }) {
  const open = atoms.some((a) => a.spin != null);
  return (
    <details className="card">
      <summary><h2 style={{ display: "inline" }}>Atoms</h2> <span className="secondary">({atoms.length}, {method})</span></summary>
      <p className="secondary">
        Löwdin charge{open ? " and spin population (unpaired electron density)" : ""} on each atom, the sum of its
        bond orders, and Mayer's free valence: bonding capacity the atom has left, about 1 on an atom carrying an
        unpaired electron. Hover an atom in the 3D view for the same numbers.
      </p>
      <table>
        <thead>
          <tr>
            <th>Atom</th><th className="num">Charge</th>{open && <th className="num">Spin</th>}
            <th className="num">Σ bond order</th><th className="num">Free valence</th>
          </tr>
        </thead>
        <tbody>
          {atoms.map((a) => (
            <tr key={a.name}>
              <td>{a.name}</td>
              <td className="num">{signed(a.charge, 3)}</td>
              {open && <td className="num">{a.spin == null ? "–" : signed(a.spin, 3)}</td>}
              <td className="num">{a.bondSum.toFixed(3)}</td>
              <td className="num">{a.freeValence == null ? "–" : a.freeValence.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}


function HaloLegend({ kind, animating }: { kind: Exclude<Highlight, "none">; animating: boolean }) {
  if (animating) return <span className="secondary">Halos return when the vibration stops.</span>;
  const full = HALO_FULL[kind];
  const samples = [-full, -full / 2, full / 2, full];
  const name = kind === "charge" ? "Löwdin charge" : "Spin population";
  return (
    <figure className="row" style={{ gap: 8, alignItems: "center", margin: 0 }} aria-label={`${name} legend`}>
      <figcaption className="secondary">{name}</figcaption>
      {samples.map((v) => {
        const st = haloStyle(v, kind)!;
        return (
          <span key={v} className="row" style={{ gap: 3, alignItems: "center" }}>
            <svg width="18" height="18" aria-hidden="true">
              <circle cx="9" cy="9" r={st.radius * 12} fill={`var(${st.color})`} fillOpacity={st.opacity} />
              <circle cx="9" cy="9" r="3" fill="var(--text-muted)" />
            </svg>
            <span className="secondary">{signed(v, 2)}</span>
          </span>
        );
      })}
      <span className="secondary">· fixed scale for every species; |{kind}| &lt; {(0.02 * full).toFixed(2)} not drawn</span>
    </figure>
  );
}

