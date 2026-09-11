"""Request and response schemas.

`QuerySpec` is the one description of a question this API can answer. The GET
endpoints deserialize their query parameters into it and `POST /query` accepts it
as JSON, so both paths share a single validator and a single SQL builder. When the
natural-language query mode arrives, it emits a QuerySpec too -- it gains no SQL
surface of its own.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .registry import FACETS_BY_FIELD, GRAINS, GRAIN_ORDER, MEASURES, METADATA_FACETS


class Provenance(str, Enum):
    """How a number in a response came to be.

    Reporting this is what lets the dashboards honour the decks' "dynamically
    recalculated" requirement without ever showing a figure the cube cannot support.
    """

    EXACT = "exact"            # read from the stored aggregate row at this grain
    AGGREGATED = "aggregated"  # additive counts summed up from a finer grain
    APPROXIMATE = "approximate"  # count-weighted mean of pre-aggregated means
    UNAVAILABLE = "unavailable"  # cannot be recovered from pre-aggregated data
    EMPTY = "empty"            # column exists but holds no values in this dataset


class Filters(BaseModel):
    """Uniform filter set, applied identically by every endpoint."""

    study_id: List[int] = Field(default_factory=list)
    subject_id: List[int] = Field(default_factory=list)
    sample_id: List[int] = Field(default_factory=list)

    chain: List[str] = Field(default_factory=list)
    celltype_id: List[int] = Field(default_factory=list)
    allele_id: List[int] = Field(default_factory=list)
    allele_segment: List[str] = Field(default_factory=list)
    allele_gene: List[str] = Field(default_factory=list)

    #: Entity metadata filters, keyed by facet field name. Values are matched with
    #: `= ANY($n)`. Only fields declared in the registry are accepted.
    metadata: Dict[str, List[str]] = Field(default_factory=dict)

    age_min: Optional[float] = None
    age_max: Optional[float] = None
    time_collected_from: Optional[datetime] = None
    time_collected_to: Optional[datetime] = None

    @field_validator("metadata")
    @classmethod
    def _known_metadata_fields(cls, value: Dict[str, List[str]]) -> Dict[str, List[str]]:
        allowed = {f.field for f in METADATA_FACETS if f.kind == "categorical"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                f"unknown metadata filter(s): {', '.join(unknown)}. "
                f"Allowed: {', '.join(sorted(allowed))}"
            )
        return {k: v for k, v in value.items() if v}

    @field_validator("chain")
    @classmethod
    def _normalise_chain(cls, value: List[str]) -> List[str]:
        return [v.strip().upper() for v in value if v.strip()]

    # -- introspection used by the query builder -------------------------------

    def levels_narrowed(self) -> set:
        """Entity levels this filter set cuts into.

        A `study_id` filter selects whole studies, so a study-grain aggregate row is
        still exactly right. A `sample_id` filter cuts *inside* a study, so study-grain
        rows must be recomputed from the sample grain.
        """
        levels = set()
        if self.study_id:
            levels.add("study")
        if self.subject_id:
            levels.add("subject")
        if self.sample_id:
            levels.add("sample")
        for field_name in self.metadata:
            levels.add(FACETS_BY_FIELD[field_name].level)
        if self.age_min is not None or self.age_max is not None:
            levels.add("subject")
        if self.time_collected_from is not None or self.time_collected_to is not None:
            levels.add("sample")
        return levels

    def cuts_below(self, grain: str) -> bool:
        """True when the filter set selects part of an entity at `grain`."""
        target = GRAIN_ORDER[grain]
        return any(GRAIN_ORDER[level] > target for level in self.levels_narrowed())

    def dimensions_active(self) -> set:
        active = set()
        if self.chain:
            active.add("chain")
        if self.celltype_id:
            active.add("annotated_celltype_id")
        if self.allele_id or self.allele_segment or self.allele_gene:
            active.add("vj_allele_id")
        return active

    def any_active(self) -> bool:
        return bool(self.levels_narrowed() or self.dimensions_active())


class SortSpec(BaseModel):
    column: str
    descending: bool = True


class QuerySpec(BaseModel):
    """A complete, validated description of one question."""

    measure: str = "summary"
    grain: str = "sample"
    filters: Filters = Field(default_factory=Filters)
    sort: Optional[SortSpec] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=5000)

    @field_validator("grain")
    @classmethod
    def _known_grain(cls, value: str) -> str:
        if value not in GRAINS:
            raise ValueError(f"grain must be one of {', '.join(GRAINS)}")
        return value

    @field_validator("measure")
    @classmethod
    def _known_measure(cls, value: str) -> str:
        if value not in MEASURES:
            raise ValueError(f"measure must be one of {', '.join(MEASURES)}")
        return value

    @model_validator(mode="after")
    def _measure_supports_grain(self) -> "QuerySpec":
        measure = MEASURES[self.measure]
        if self.grain not in measure.tables:
            raise ValueError(
                f"measure {self.measure!r} is only available at grain(s): "
                f"{', '.join(measure.grains)}"
            )
        if self.sort is not None:
            sortable = set(measure.value_columns) | set(measure.dims) | {
                f"{self.grain}_id",
                f"{self.grain}_name",
            }
            if self.sort.column not in sortable:
                raise ValueError(
                    f"cannot sort {self.measure!r} by {self.sort.column!r}. "
                    f"Sortable: {', '.join(sorted(sortable))}"
                )
        return self


# -- responses ---------------------------------------------------------------


class FacetValue(BaseModel):
    value: Any
    label: str
    count: Optional[int] = None


class FacetAvailability(BaseModel):
    field: str
    label: str
    level: str
    kind: str
    available: bool
    distinct_count: int
    derived: bool = False
    note: str = ""
    values: List[FacetValue] = Field(default_factory=list)
    min: Optional[float] = None
    max: Optional[float] = None


class QueryResult(BaseModel):
    spec: QuerySpec
    total: int
    page: int
    page_size: int
    columns: List[str]
    rows: List[Dict[str, Any]]
    provenance: Dict[str, Provenance]
    notes: List[str] = Field(default_factory=list)


class Kpi(BaseModel):
    key: str
    label: str
    value: Optional[float] = None
    provenance: Provenance = Provenance.EXACT
    note: str = ""


class Breakdown(BaseModel):
    key: str
    label: str
    source: str  # the measure the breakdown was served from
    provenance: Provenance
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    note: str = ""


class Dashboard(BaseModel):
    level: str
    study_id: Optional[int] = None
    filters: Filters
    kpis: List[Kpi]
    breakdowns: Dict[str, Breakdown]
    notes: List[str] = Field(default_factory=list)
