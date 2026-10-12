import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { GridOut, StateDetail } from "../api/client";
import { GridView } from "./GridView";
import { SpeciesView } from "./SpeciesView";
import { Thumbnail } from "../components/Thumbnail";
import { LangProvider, type Lang } from "../i18n";

vi.mock("3dmol", () => ({
  createViewer: () => ({
    addModel: () => ({ vibrate: vi.fn(), selectedAtoms: () => [{}, {}, {}] }),
    setStyle: vi.fn(), zoomTo: vi.fn(), zoom: vi.fn(), render: vi.fn(), clear: vi.fn(),
    animate: vi.fn(), stopAnimate: vi.fn(), resize: vi.fn(),
    setHoverable: vi.fn(), setHoverDuration: vi.fn(), addCylinder: vi.fn(), addLabel: vi.fn(), removeLabel: vi.fn(),
  }),
}));

const brief = (over: Partial<StateDetail> = {}) => ({
  m: 3, charge: 1, mult: 1, label: "H3+ (1)", verdict: "bound_with_zpe" as const,
  d_e: 0.169, d_0: 0.158, d_h: 0.16, d_g: 0.15, channel: "H2 + H+", channel_g: "H2 + H+",
  spin_gap: 0, structure_id: 7, point_group: "D3h", shape: "planar", composition: "H3",
  ...over,
});

const grid: GridOut = {
  campaign: "mini", temperature: 298.15, pressure: 1, quantity: "d_e",
  cells: [
    { m: 3, charge: 1, species: "H3+", ground: brief(), value: 4.601, survives: true,
      xyz: "3\n\nH 0 0 0\nH 0.87 0 0\nH 0.435 0.753 0\n", states: [brief()] },
    { m: 2, charge: -1, species: "H2-", ground: brief({ m: 2, charge: -1, mult: 2, label: "H2- (2)", verdict: "unbound_electron", d_e: null, structure_id: null }),
      value: null, survives: null, xyz: null, states: [] },
  ],
};

const detail: StateDetail = {
  ...brief(), campaign: "mini", temperature: 298.15, pressure: 1, energy: -1.34, zpe: 0.0207,
  geometry_level: "L1M", xyz: "3\n\nH 0 0 0\nH 0.87 0 0\nH 0.435 0.753 0\n",
  homo: -33.6, lumo: -2.1, gap: 31.5, s2: null, spin_contaminated: null, detachment: null,
  ionization: null, radius_of_gyration: 0.5,
  channels: [
    { split: "H + H2+", limit: "H2 + H+", d_e: 4.601, d_0: 4.313, d_g: 4.08 },
    { split: "H+ + H2", limit: "H2 + H+", d_e: 4.601, d_0: 4.313, d_g: 4.08 },
  ],
  isomers: [{ structure_id: 7, ref_job_id: 11, geometry_level: "L1M", energy: -1.34, relative: 0, point_group: "D3h", shape: "planar", composition: "H3" }],
  multiplicities: [brief()],
};

const bonds = {
  structure_id: 7, method: "ωB97X-D4/def2-TZVPPD", mayer: [{ i: 0, j: 1, order: 0.44 }],
  loewdin: [{ i: 0, j: 1, order: 0.444 }, { i: 0, j: 2, order: 0.444 }, { i: 1, j: 2, order: 0.444 }],
  atoms: [0, 1, 2].map(() => ({ charge: 0.333, spin: null, valence: 0.89, free_valence: 0 })),
};

function respond(url: string): Response {
  const body = url.includes("/grid") ? grid
    : url.includes("/structures/7/bonds") ? bonds
    : url.includes("/states/3/1/1") ? detail
    : url.includes("/modes") ? null
    : url.includes("/api/campaigns") ? [{ name: "mini", n_states: 2, n_jobs: 3 }]
    : null;
  return new Response(JSON.stringify(body ?? { detail: "not found" }), {
    status: body ? 200 : 404, headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) =>
    respond(typeof input === "string" ? input : input instanceof URL ? input.href : input.url)));
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function renderAt(path: string, lang: Lang = "en") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <LangProvider lang={lang}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/c/:campaign" element={<GridView />} />
            <Route path="/c/:campaign/s/:m/:charge/:mult" element={<SpeciesView />} />
          </Routes>
        </MemoryRouter>
      </LangProvider>
    </QueryClientProvider>,
  );
}

describe("GridView", () => {
  it("shows one cell per species with its verdict and value", async () => {
    renderAt("/c/mini");
    const cell = await screen.findByRole("gridcell", { name: /^H3\+ \(1\): bound with ZPE/ });
    expect(cell).toHaveAttribute("href", "/c/mini/s/3/1/1");
    expect(within(cell).getByText("+4.60")).toBeInTheDocument();
    expect(screen.getByRole("gridcell", { name: /^H2- \(2\): electron unbound/ })).toBeInTheDocument();
    expect(screen.getAllByText("bare proton")).toHaveLength(1);
    expect(screen.getAllByText("not computed").length).toBeGreaterThan(0);
  });

  it("asks the API for the conditions in the URL", async () => {
    renderAt("/c/mini?q=d_g&T=1000&p=0.5&color=value");
    await screen.findByRole("gridcell", { name: /^H3\+/ });
    const urls = vi.mocked(fetch).mock.calls.map(([input]) => (input instanceof Request ? input.url : String(input)));
    const url = urls.find((u) => u.includes("/grid")) ?? "";
    expect(url).toContain("quantity=d_g");
    expect(url).toContain("temperature=1000");
    expect(url).toContain("pressure=0.5");
    expect(screen.getByText(/D_G \(eV\): falls apart/)).toBeInTheDocument(); // value legend
  });

  it("the verdict follows the selected D, and T and p hide when they do not matter", async () => {
    const { unmount } = renderAt("/c/mini?q=d_e");
    await screen.findByRole("gridcell", { name: /^H3\+ \(1\): bound \(D_e > 0\)/ });
    expect(document.getElementById("temperature")).toBeNull();
    expect(screen.queryByRole("button", { name: "Reset" })).not.toBeInTheDocument();
    unmount();
    renderAt("/c/mini?q=d_g&T=20&p=0.001");
    await screen.findByRole("gridcell", { name: /^H3\+ \(1\): holds together at T and p/ });
    expect(screen.getByText("holds together at 20.0 K, 1.0e-3 atm (D_G > 0)")).toBeInTheDocument();
    expect(document.getElementById("temperature")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(await screen.findByText("holds together at 298 K, 1.00 atm (D_G > 0)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset" })).toBeDisabled();
  });

  it("the table shows every D, coloured, with only T and p, and picks D from its headings", async () => {
    renderAt("/c/mini?q=d_e");
    await screen.findByRole("gridcell", { name: /^H3\+/ });
    fireEvent.click(screen.getByRole("button", { name: "Table" }));
    expect(screen.queryByRole("group", { name: "Colour by" })).not.toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Dissociation energy" })).not.toBeInTheDocument();
    expect(document.getElementById("temperature")).toBeInTheDocument(); // D_H, D_G need T and p
    expect(document.getElementById("pressure")).toBeInTheDocument();
    expect(screen.queryByLabelText("Colour key")).not.toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getByRole("button", { name: "D_e" })).toHaveAttribute("aria-pressed", "true");
    expect(within(table).getByText("bound (D_e > 0)")).toHaveStyle({ background: "var(--ord-2)" });
    expect(within(table).getByLabelText("D_e 0.169 eV")).toHaveStyle({ background: "var(--div-pos-2)" });
    expect(within(table).getAllByText("+0.150")[0]).toHaveStyle({ background: "var(--div-pos-2)" }); // D_G coloured too

    fireEvent.click(within(table).getByRole("button", { name: "D_G" }));
    expect(await within(table).findByText("holds together at T and p (D_G > 0)")).toBeInTheDocument();
    expect(within(table).getByText("Weakest channel (D_G)")).toBeInTheDocument();
    const urls = vi.mocked(fetch).mock.calls.map(([input]) => (input instanceof Request ? input.url : String(input)));
    expect(urls.some((u) => u.includes("/grid") && u.includes("quantity=d_g"))).toBe(true);
  });
});

describe("in Japanese", () => {
  it("the grid speaks Japanese, formulas and numbers unchanged", async () => {
    renderAt("/c/mini", "ja");
    const cell = await screen.findByRole("gridcell", { name: /^H3\+ \(1\): 零点エネルギー込みで束縛/ });
    expect(within(cell).getByText("+4.60")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("どの水素クラスターがまとまっていられるか");
    expect(screen.getByRole("rowheader", { name: "アニオン" })).toBeInTheDocument();
    expect(screen.getAllByText("裸の陽子")).toHaveLength(1);
  });
  it("the species page too", async () => {
    renderAt("/c/mini/s/3/1/1", "ja");
    expect(await screen.findByText("分解の経路")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("H₃⁺ 一重項");
    expect(screen.getByText("D3h · 平面")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "結合次数" })).toBeInTheDocument();
  });
});

describe("SpeciesView", () => {
  it("shows the weakest channel, the properties and the raw files", async () => {
    renderAt("/c/mini/s/3/1/1");
    expect(await screen.findByText("Ways to fall apart")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("H₃⁺");
    expect(screen.getAllByText("+4.601").length).toBeGreaterThan(0);
    expect(screen.getByText("D3h · planar")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "output" })).toHaveAttribute("href", "/api/jobs/11/files/job.out");
    // bond orders and atoms from the bonds study
    expect(await screen.findByText("H1–H2")).toBeInTheDocument();
    const atoms = within(screen.getByRole("heading", { name: "Atoms" }).closest("details")!);
    expect(atoms.getAllByRole("row")).toHaveLength(4);
    expect(atoms.getAllByText("+0.333")).toHaveLength(3);
    expect(atoms.getAllByText("0.888")).toHaveLength(3); // 2 × 0.444
    expect(atoms.queryByText("Spin")).toBeNull(); // closed shell
  });

  it("the channels card shows T and p only for D_G", async () => {
    renderAt("/c/mini/s/3/1/1");
    const card = within((await screen.findByText("Ways to fall apart")).closest(".card") as HTMLElement);
    expect(document.getElementById("channels-temperature")).toBeNull();
    fireEvent.click(card.getByRole("button", { name: "D_G" }));
    expect(document.getElementById("channels-temperature")).toBeInTheDocument();
    expect(document.getElementById("channels-pressure")).toBeInTheDocument();
    expect(card.getByRole("button", { name: "Reset" })).toBeDisabled();
  });
});

describe("Thumbnail", () => {
  const triangle = "3\n\nH 0 0 0\nH 0.87 0 0\nH 0.435 0.753 0\n";
  const lines = (el: HTMLElement) => el.querySelectorAll("line").length;
  it("draws the bonds it is given (bond order > 0.33) instead of the distance rule", () => {
    const { container } = render(<Thumbnail xyz={triangle} bonds={[[0, 1]]} />);
    expect(lines(container)).toBe(1);
  });
  it("falls back to distances without bond orders", () => {
    expect(lines(render(<Thumbnail xyz={triangle} bonds={null} />).container)).toBe(3);
    expect(lines(render(<Thumbnail xyz={triangle} bonds={[]} />).container)).toBe(0); // all weak
  });
});

