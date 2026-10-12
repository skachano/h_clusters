"""Response models: the OpenAPI schema the web app's TypeScript client is generated from.

Units: dissociation and relative energies in eV, absolute energies in Eh, temperature in K,
pressure in atm, distances in Å, frequencies in cm⁻¹.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

Quantity = Literal["d_e", "d_0", "d_h", "d_g"]
TrendQuantity = Literal["binding_per_atom", "d_e", "d_0", "d_g", "second_difference", "gap"]
Verdict = Literal[
    "unbound_electron", "not_a_minimum", "dissociates", "metastable", "bound",
    "bound_with_zpe", "atom",
]


class CampaignOut(BaseModel):
    name: str
    n_states: int
    n_jobs: int


class Conditions(BaseModel):
    temperature: float = Field(description="K")
    pressure: float = Field(description="atm")


class StateBrief(BaseModel):
    m: int
    charge: int
    mult: int
    label: str
    verdict: Verdict
    d_e: float | None = Field(None, description="eV, lowest spin-allowed channel minus the state")
    d_0: float | None = None
    d_h: float | None = None
    d_g: float | None = None
    channel: str | None = Field(None, description="lowest channel for D_e")
    channel_g: str | None = Field(None, description="lowest channel for D_G")
    spin_gap: float | None = Field(None, description="eV above the species' lowest computed state")
    structure_id: int | None = None
    point_group: str | None = None
    shape: str | None = None
    composition: str | None = Field(None, description="bonded units by distance (1.15 Å) in the best structure")
    units: str | None = Field(None, description="covalent cores and ligands: the pieces left after every "
                              "split cheaper than 1 eV, e.g. 'H3+ + 2 H2'")
    cluster_units: str | None = Field(None, description="the pieces left after every split cheaper than "
                                      "0.013 eV: ion clusters whole, van der Waals units apart")


class GridCell(BaseModel):
    m: int
    charge: int
    species: str
    ground: StateBrief | None = Field(None, description="the species' lowest-energy state")
    xyz: str | None = Field(None, description="geometry of the ground state's best structure")
    bonds: list[tuple[int, int]] | None = Field(
        None, description="atom pairs (XYZ order, 0-based) with Löwdin bond order above 0.33, for the "
        "thumbnail; None when the structure has no bond orders")
    value: float | None = Field(None, description="the requested quantity of the ground state, eV")
    survives: bool | None = Field(None, description="value > 0")
    states: list[StateBrief]


class GridOut(Conditions):
    campaign: str
    quantity: Quantity
    cells: list[GridCell]


class ChannelOut(BaseModel):
    split: str = Field(description="binary split, e.g. 'H3 + H'")
    limit: str = Field(description="lowest spin-allowed fragments it leads to, e.g. 'H2 + H + H'")
    d_e: float | None
    d_0: float | None
    d_g: float | None


class FragmentChannel(BaseModel):
    split: str = Field(description="binary split into fragment states, e.g. 'H5+ + H'")
    parts: list[str] = Field(description="the fragment states (labels, keys of `fragmentation`)")
    electron: bool = Field(description="electron detachment: the second fragment is e-")
    d_e: float = Field(description="eV, fragments at their own best energies minus the state")


class UnitsOut(BaseModel):
    threshold: float = Field(description="eV: every split cheaper than this is made")
    alternatives: list[str] = Field(description="distinct sets of units reached; one unless the "
                                    "orders of splitting disagree")
    units: list[str] = Field(description="the units of the first alternative, in the order of `groups`")
    groups: list[list[int]] | None = Field(None, description="atoms (0-based, XYZ order) of each unit in the "
                                           "best structure; None without a structure")
    equivalent: int | None = Field(None, description="atom assignments as good as `groups`; > 1 means "
                                   "the units are delocalised over the structure")
    by: str | None = Field(None, description="'bond order' (Löwdin, from the bonds study) or 'distance'")


class IsomerOut(BaseModel):
    structure_id: int
    ref_job_id: int
    geometry_level: str
    energy: float = Field(description="CCSD(T), Eh")
    relative: float = Field(description="eV above the state's lowest isomer")
    point_group: str
    shape: str
    composition: str


class StateDetail(StateBrief, Conditions):
    campaign: str
    energy: float | None = Field(None, description="CCSD(T) of the best structure, Eh")
    zpe: float | None = Field(None, description="Eh")
    geometry_level: str | None = None
    xyz: str | None = None
    homo: float | None = Field(None, description="eV, HF orbitals of the reference")
    lumo: float | None = Field(None, description="eV")
    gap: float | None = Field(None, description="eV")
    s2: float | None = None
    spin_contaminated: bool | None = None
    detachment: float | None = Field(None, description="anions: eV to the lowest neutral + e- limit")
    ionization: float | None = Field(None, description="eV to the lowest cation + e- limit")
    radius_of_gyration: float | None = Field(None, description="Å")
    channels: list[ChannelOut]
    core_units: UnitsOut | None = None
    ion_cluster_units: UnitsOut | None = None
    fragmentation: dict[str, list[FragmentChannel]] = Field(
        default_factory=dict, description="state label -> its channels, cheapest first; states reached "
        "through splits cheaper than 1 eV are expanded, the root is the state's own label")
    isomers: list[IsomerOut]
    multiplicities: list[StateBrief]


class ModesOut(BaseModel):
    structure_id: int
    job_id: int
    level: str
    xyz: str
    frequencies: list[float] = Field(description="cm⁻¹, vibrations only; imaginary < 0")
    modes: list[list[list[float]]] = Field(description="(n_vib, n_atoms, 3), Cartesian displacements")


class BondOrder(BaseModel):
    i: int = Field(description="atom index (0-based, order of the structure's XYZ)")
    j: int
    order: float


class AtomProps(BaseModel):
    charge: float = Field(description="Löwdin atomic charge")
    spin: float | None = Field(description="Löwdin spin population; None for closed shells")
    valence: float | None = Field(description="Mayer total valence VA")
    free_valence: float | None = Field(description="Mayer free valence FA: ~1 on an atom with an unpaired electron")


class BondsOut(BaseModel):
    structure_id: int
    method: str
    loewdin: list[BondOrder] = Field(description="Löwdin (Wiberg-type) bond orders >= 0.001")
    mayer: list[BondOrder] = Field(description="Mayer bond orders >= 0.001 in magnitude")
    atoms: list[AtomProps] = Field(description="per atom, in the order of the structure's XYZ")


class TrendPoint(BaseModel):
    m: int
    value: float | None
    label: str | None = None


class TrendSeries(BaseModel):
    charge: int
    points: list[TrendPoint]


class TrendsOut(Conditions):
    campaign: str
    quantity: TrendQuantity
    unit: str
    series: list[TrendSeries]


class BenchmarkPoint(BaseModel):
    label: str
    m: int
    charge: int
    mult: int
    reference: float = Field(description="D_e at CCSD(T), eV")
    test: float = Field(description="D_e at the test level, eV")


class BenchmarkOut(BaseModel):
    campaign: str
    test: str
    reference: str
    quantity: str = "d_e"
    n: int
    mae: float | None = Field(None, description="eV")
    max_abs: float | None = Field(None, description="eV")
    points: list[BenchmarkPoint]


class StageSummary(BaseModel):
    stage: str
    level: str
    counts: dict[str, int]
    retried: int
    cpu_hours: float
    wall_median_s: float | None
    histogram_edges_s: list[float]
    histogram_counts: list[int]


class FailureOut(BaseModel):
    job_id: int
    label: str
    stage: str
    status: str
    error_kind: str | None
    error: str | None
    attempts: int


class JobsSummaryOut(BaseModel):
    campaign: str
    counts: dict[str, int]
    stages: list[StageSummary]
    failures: list[FailureOut]


class AttemptOut(BaseModel):
    n: int
    hash: str | None
    modifiers: list[str]
    status: str
    error_kind: str | None
    error: str | None
    action: str | None
    cached: bool
    wall_s: float | None


class JobOut(BaseModel):
    id: int
    campaign: str
    label: str
    stage: str
    level: str
    task: str
    status: str
    attempts: int
    hash: str | None
    parent_id: int | None
    input_structure_id: int
    error_kind: str | None
    error: str | None
    wall_s: float | None
    files: list[str]
    history: list[AttemptOut]


class StudyOut(BaseModel):
    """A Phase 8 study report: one row per item, columns depend on the study."""

    campaign: str
    name: str
    rows: list[dict[str, Any]]
