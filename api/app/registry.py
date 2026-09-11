"""The allowlist.

Every table name, column name and filterable field the API will ever emit into SQL
is declared here. Request input selects *entries* from these structures; it never
becomes an identifier. That is what keeps the query builder injection-proof, and it
is what will keep the v2 natural-language path safe when it emits a QuerySpec.

The database is a pre-aggregated cube: 3 grains x 6 measures. One declarative map
covers all 21 combinations, so adding a grain or measure is a data change, not code.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

GRAINS: Tuple[str, ...] = ("study", "subject", "sample")

#: The identifying column at each grain.
GRAIN_KEY: Dict[str, str] = {g: f"{g}_id" for g in GRAINS}

#: Coarse -> fine. A filter at a finer grain than the one being requested means the
#: stored aggregate rows no longer answer the question and must be recomputed.
GRAIN_ORDER: Dict[str, int] = {"study": 0, "subject": 1, "sample": 2}

ISOTYPE_COLUMNS: Tuple[str, ...] = (
    "count_igm",
    "count_igd",
    "count_iga",
    "count_igg",
    "count_ige",
)

SUMMARY_COUNTS: Tuple[str, ...] = (
    "count_bcrs",
    "count_igh_igk_pair",
    "count_igh_igl_pair",
) + ISOTYPE_COLUMNS

CDR3_PERCENTILES: Tuple[str, ...] = (
    "cdr3_median",
    "cdr3_p05",
    "cdr3_p25",
    "cdr3_p75",
    "cdr3_p95",
)

MUTFREQ_COLUMNS: Tuple[str, ...] = (
    "mutfreq_mean",
    "mutfreq_median",
    "mutfreq_p05",
    "mutfreq_p25",
    "mutfreq_p75",
    "mutfreq_p95",
)


@dataclass(frozen=True)
class Measure:
    """One face of the cube.

    `additive` columns survive being summed across a finer grain, so they can be
    recomputed under any filter. `means` can be count-weighted into a defensible
    approximation. `percentiles` cannot be recovered from pre-aggregated rows at
    all -- under a filter that forces recomputation they are returned as null with
    provenance `unavailable`, never as a plausible-looking wrong number.
    """

    name: str
    label: str
    tables: Dict[str, str]
    dims: Tuple[str, ...] = ()
    additive: Tuple[str, ...] = ()
    means: Tuple[str, ...] = ()
    percentiles: Tuple[str, ...] = ()
    extremes: Tuple[str, ...] = ()  # aggregated with MAX
    weight: Optional[str] = None  # column weighting `means`
    empty_columns: Tuple[str, ...] = ()  # known-empty in the current dump

    @property
    def grains(self) -> Tuple[str, ...]:
        return tuple(g for g in GRAINS if g in self.tables)

    @property
    def value_columns(self) -> Tuple[str, ...]:
        return self.additive + self.means + self.percentiles + self.extremes

    def table_for(self, grain: str) -> str:
        try:
            return self.tables[grain]
        except KeyError:
            raise KeyError(f"measure {self.name!r} is not available at grain {grain!r}")


def _per_grain(suffix: str) -> Dict[str, str]:
    return {g: f"{g}{suffix}" for g in GRAINS}


MEASURES: Dict[str, Measure] = {
    "summary": Measure(
        name="summary",
        label="Repertoire summary",
        tables=_per_grain("_summary"),
        additive=SUMMARY_COUNTS,
    ),
    "chain": Measure(
        name="chain",
        label="Chain statistics",
        tables=_per_grain("_chain_summary"),
        dims=("chain",),
        additive=("count_chain",),
        means=("cdr3_mean", "mutfreq_mean"),
        percentiles=CDR3_PERCENTILES + MUTFREQ_COLUMNS[1:],
        weight="count_chain",
        empty_columns=MUTFREQ_COLUMNS,
    ),
    "celltype": Measure(
        name="celltype",
        label="Cell type statistics",
        tables=_per_grain("_annotated_celltype"),
        dims=("annotated_celltype_id",),
        additive=("count_bcrs",) + ISOTYPE_COLUMNS,
    ),
    "chain_celltype": Measure(
        name="chain_celltype",
        label="Chain x cell type statistics",
        tables=_per_grain("_chain_annotated_celltype_summary"),
        dims=("chain", "annotated_celltype_id"),
        additive=("count_chain",),
        means=("cdr3_mean", "mutfreq_mean"),
        percentiles=CDR3_PERCENTILES + MUTFREQ_COLUMNS[1:],
        weight="count_chain",
        empty_columns=MUTFREQ_COLUMNS,
    ),
    "allele": Measure(
        name="allele",
        label="V/J allele usage",
        tables=_per_grain("_vj_allele"),
        dims=("vj_allele_id",),
        additive=("count_vj_allele",),
    ),
    "allele_celltype": Measure(
        name="allele_celltype",
        label="V/J allele usage by cell type",
        tables=_per_grain("_vj_allele_annotated_celltype"),
        dims=("vj_allele_id", "annotated_celltype_id"),
        additive=("count_vj_allele",),
    ),
    # clonesize_* columns exist only on study_summary -- there is no subject or
    # sample equivalent, so this measure is study-grain only.
    "clonesize": Measure(
        name="clonesize",
        label="Clone size",
        tables={"study": "study_summary"},
        means=("clonesize_mean",),
        percentiles=(
            "clonesize_median",
            "clonesize_p05",
            "clonesize_p25",
            "clonesize_p75",
            "clonesize_p95",
        ),
        extremes=("largest_clonesize",),
    ),
}


@dataclass(frozen=True)
class Dimension:
    """A dimension column, plus where its human-readable label lives."""

    key: str
    label: str
    table: Optional[str] = None
    name_column: Optional[str] = None

    @property
    def is_lookup(self) -> bool:
        return self.table is not None


DIMENSIONS: Dict[str, Dimension] = {
    "chain": Dimension(key="chain", label="Chain"),
    "annotated_celltype_id": Dimension(
        key="annotated_celltype_id",
        label="Cell type",
        table="annotated_celltype",
        name_column="annotated_celltype_name",
    ),
    "vj_allele_id": Dimension(
        key="vj_allele_id",
        label="V/J allele",
        table="vj_allele",
        name_column="vj_allele_name",
    ),
}


@dataclass(frozen=True)
class Facet:
    """A filterable field, and the entity table it lives on.

    `available` is not declared here -- it is measured at runtime against the data
    (see services.facets). Every facet the design decks ask for is declared, and the
    ones with no values in the current dump simply report available=false until the
    real dataset populates them.
    """

    field: str
    label: str
    level: str  # study | subject | sample
    column: str
    kind: str = "categorical"  # categorical | numeric | temporal
    derived: bool = False
    note: str = ""


#: Entity metadata facets. Almost all of these are 100% NULL in the test dump; they
#: are declared anyway so the UI lights them up automatically once metadata lands.
METADATA_FACETS: Tuple[Facet, ...] = (
    Facet("organism", "Organism", "subject", "organism"),
    Facet("strain", "Strain", "subject", "strain"),
    Facet("biological_sex", "Sex", "subject", "biological_sex"),
    Facet("age", "Age", "subject", "age", kind="numeric"),
    Facet("ethnicity", "Ethnicity", "subject", "ethnicity"),
    Facet("race", "Race", "subject", "race"),
    Facet("disease_reported", "Disease", "subject", "disease_reported"),
    Facet("disease_stage", "Disease stage", "subject", "disease_stage"),
    Facet("exposure_process_reported", "Exposure process", "subject", "exposure_process_reported"),
    Facet("exposure_material_reported", "Exposure material", "subject", "exposure_material_reported"),
    Facet("batch", "Batch", "sample", "batch"),
    Facet("tissue", "Tissue", "sample", "tissue"),
    Facet("cell_type", "Sample cell type", "sample", "cell_type",
          note="The sample-level cell_type column, distinct from annotated cell types."),
    Facet("treatment", "Treatment", "sample", "treatment"),
    Facet("molecule", "Molecule", "sample", "molecule"),
    Facet("time_collected", "Time collected", "sample", "time_collected", kind="temporal"),
    Facet("time_t0_event", "T0 event", "sample", "time_t0_event"),
)

#: Dimension facets -- these are backed by the cube itself and always have values.
DIMENSION_FACETS: Tuple[Facet, ...] = (
    Facet("chain", "Chain", "sample", "chain"),
    Facet("celltype_id", "Cell type", "sample", "annotated_celltype_id"),
    Facet("allele_id", "V/J allele", "sample", "vj_allele_id"),
    Facet("allele_segment", "Allele segment", "sample", "vj_allele_name", derived=True,
          note="Derived from the allele name, e.g. IGHV, IGKJ."),
    Facet("allele_gene", "Allele gene", "sample", "vj_allele_name", derived=True,
          note="Derived from the allele name, e.g. IGHV1-18."),
)

FACETS: Tuple[Facet, ...] = DIMENSION_FACETS + METADATA_FACETS

FACETS_BY_FIELD: Dict[str, Facet] = {f.field: f for f in FACETS}

#: Entity tables the scope CTE may filter on, and the columns exposed for each.
ENTITY_TABLES: Dict[str, str] = {"study": "study", "subject": "subject", "sample": "sample"}

#: Denormalized entity views used by the entity endpoints.
ENTITY_VIEWS: Dict[str, str] = {
    "study": "ui.study_overview_view",
    "subject": "ui.subject_overview_view",
    "sample": "ui.sample_overview_view",
}

#: Columns carried through to every exported row, per the decks' requirement that
#: output records are "clearly tagged with the corresponding study name".
BREADCRUMB_COLUMNS: Dict[str, Tuple[str, ...]] = {
    "study": ("study_id", "study_name"),
    "subject": ("study_id", "study_name", "subject_id", "subject_name"),
    "sample": ("study_id", "study_name", "subject_id", "subject_name", "sample_id", "sample_name"),
}


def measure_or_400(name: str) -> Measure:
    if name not in MEASURES:
        raise KeyError(name)
    return MEASURES[name]
