"""SQL construction for the aggregate cube.

Two paths, chosen by whether the filter set cuts below the requested grain:

* **exact** -- the stored aggregate rows still answer the question, so read them.
* **aggregated** -- recompute from the sample grain. Counts are additive so they
  come back correct; means become count-weighted approximations; percentiles are
  not recoverable from pre-aggregated data and are returned as NULL rather than as
  a plausible-looking wrong number.

Identifiers are never taken from request input -- every table and column name comes
from `registry`.
"""
from typing import Any, Dict, List, Optional, Tuple

from .models import Filters, Provenance, QuerySpec
from .registry import (
    BREADCRUMB_COLUMNS,
    DIMENSIONS,
    FACETS_BY_FIELD,
    GRAIN_KEY,
    Measure,
    MEASURES,
)


class Params:
    """Accumulates bind parameters and hands back `$n` placeholders."""

    def __init__(self) -> None:
        self.values: List[Any] = []

    def add(self, value: Any) -> str:
        self.values.append(value)
        return f"${len(self.values)}"


# -- scope -------------------------------------------------------------------

_SEGMENT_EXPR = "substring({alias}.vj_allele_name from '^IG[HKL][VJ]')"
_GENE_EXPR = "split_part({alias}.vj_allele_name, '*', 1)"


def scope_cte(filters: Filters, params: Params) -> str:
    """Resolve any filter combination down to the sample grain.

    Everything hangs off `sample`, the finest grain, so one CTE serves all three
    grains: a study-grain query groups its `study_id` column, a sample-grain query
    uses `sample_id` directly.
    """
    where: List[str] = []

    if filters.study_id:
        where.append(f"sub.study_id = ANY({params.add(filters.study_id)})")
    if filters.subject_id:
        where.append(f"sm.subject_id = ANY({params.add(filters.subject_id)})")
    if filters.sample_id:
        where.append(f"sm.sample_id = ANY({params.add(filters.sample_id)})")

    alias_for_level = {"study": "st", "subject": "sub", "sample": "sm"}
    for field_name, values in filters.metadata.items():
        facet = FACETS_BY_FIELD[field_name]
        alias = alias_for_level[facet.level]
        where.append(f"{alias}.{facet.column} = ANY({params.add(values)})")

    if filters.age_min is not None:
        where.append(f"sub.age >= {params.add(filters.age_min)}")
    if filters.age_max is not None:
        where.append(f"sub.age <= {params.add(filters.age_max)}")
    if filters.time_collected_from is not None:
        where.append(f"sm.time_collected >= {params.add(filters.time_collected_from)}")
    if filters.time_collected_to is not None:
        where.append(f"sm.time_collected <= {params.add(filters.time_collected_to)}")

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return f"""scope AS (
    SELECT sm.sample_id, sm.subject_id, sub.study_id
    FROM sample sm
    JOIN subject sub ON sub.subject_id = sm.subject_id
    JOIN study st ON st.study_id = sub.study_id
    {clause}
)"""


# -- dimensions --------------------------------------------------------------


def dimension_joins(measure: Measure, alias: str) -> Tuple[List[str], List[str]]:
    """Name lookups for the dimension ids a measure carries."""
    joins: List[str] = []
    columns: List[str] = []
    if "annotated_celltype_id" in measure.dims:
        joins.append(
            f"LEFT JOIN annotated_celltype ct "
            f"ON ct.annotated_celltype_id = {alias}.annotated_celltype_id"
        )
        columns.append("ct.annotated_celltype_name")
    if "vj_allele_id" in measure.dims:
        joins.append(f"LEFT JOIN vj_allele va ON va.vj_allele_id = {alias}.vj_allele_id")
        columns.extend(
            [
                "va.vj_allele_name",
                f"{_SEGMENT_EXPR.format(alias='va')} AS vj_allele_segment",
                f"{_GENE_EXPR.format(alias='va')} AS vj_allele_gene",
            ]
        )
    return joins, columns


def dimension_filters(
    measure: Measure, filters: Filters, params: Params, alias: str
) -> Tuple[List[str], List[str], List[str]]:
    """Filters applied to the measure table itself.

    Returns (conditions, extra joins, notes). A filter on a dimension the measure
    does not carry is *not* silently dropped -- it is reported in the notes, because
    quietly returning unfiltered numbers is how a dashboard lies.
    """
    conditions: List[str] = []
    joins: List[str] = []
    notes: List[str] = []

    if filters.chain:
        if "chain" in measure.dims:
            conditions.append(f"{alias}.chain = ANY({params.add(filters.chain)})")
        else:
            notes.append(
                f"Chain filter not applied: measure '{measure.name}' has no chain "
                f"dimension. Use 'chain' or 'chain_celltype' to break down by chain."
            )

    if filters.celltype_id:
        if "annotated_celltype_id" in measure.dims:
            conditions.append(
                f"{alias}.annotated_celltype_id = ANY({params.add(filters.celltype_id)})"
            )
        else:
            notes.append(
                f"Cell type filter not applied: measure '{measure.name}' has no cell "
                f"type dimension."
            )

    allele_filters = filters.allele_id or filters.allele_segment or filters.allele_gene
    if allele_filters:
        if "vj_allele_id" in measure.dims:
            if filters.allele_id:
                conditions.append(
                    f"{alias}.vj_allele_id = ANY({params.add(filters.allele_id)})"
                )
            if filters.allele_segment or filters.allele_gene:
                joins.append(
                    f"LEFT JOIN vj_allele vaf ON vaf.vj_allele_id = {alias}.vj_allele_id"
                )
                if filters.allele_segment:
                    conditions.append(
                        f"{_SEGMENT_EXPR.format(alias='vaf')} = "
                        f"ANY({params.add([s.upper() for s in filters.allele_segment])})"
                    )
                if filters.allele_gene:
                    conditions.append(
                        f"{_GENE_EXPR.format(alias='vaf')} = "
                        f"ANY({params.add(filters.allele_gene)})"
                    )
        else:
            notes.append(
                f"Allele filter not applied: measure '{measure.name}' has no allele "
                f"dimension."
            )

    return conditions, joins, notes


# -- breadcrumb --------------------------------------------------------------


def breadcrumb(grain: str, alias: str) -> Tuple[List[str], List[str]]:
    """study -> subject -> sample identity carried onto every row.

    The decks require exported records to be tagged with the study name; doing it
    here means every endpoint and every export inherits it.
    """
    if grain == "study":
        return (
            ["st.study_id", "st.study_name"],
            [f"JOIN study st ON st.study_id = {alias}.study_id"],
        )
    if grain == "subject":
        return (
            ["st.study_id", "st.study_name", "sub.subject_id", "sub.subject_name"],
            [
                f"JOIN subject sub ON sub.subject_id = {alias}.subject_id",
                "JOIN study st ON st.study_id = sub.study_id",
            ],
        )
    return (
        [
            "st.study_id",
            "st.study_name",
            "sub.subject_id",
            "sub.subject_name",
            "sm.sample_id",
            "sm.sample_name",
        ],
        [
            f"JOIN sample sm ON sm.sample_id = {alias}.sample_id",
            "JOIN subject sub ON sub.subject_id = sm.subject_id",
            "JOIN study st ON st.study_id = sub.study_id",
        ],
    )


# -- value columns -----------------------------------------------------------


def value_columns_exact(measure: Measure, alias: str) -> Tuple[List[str], Dict[str, Provenance]]:
    """Stored rows: values pass through untouched, counts coalesced to 0.

    The pipeline writes NULL rather than 0 for an isotype it never observed. Serving
    that raw would make every client chart break differently, so 0 is the contract.
    """
    columns: List[str] = []
    provenance: Dict[str, Provenance] = {}
    for col in measure.additive:
        columns.append(f"COALESCE({alias}.{col}, 0) AS {col}")
        provenance[col] = Provenance.EXACT
    for col in measure.means + measure.percentiles + measure.extremes:
        columns.append(f"{alias}.{col}")
        provenance[col] = (
            Provenance.EMPTY if col in measure.empty_columns else Provenance.EXACT
        )
    return columns, provenance


def value_columns_aggregated(
    measure: Measure, alias: str
) -> Tuple[List[str], Dict[str, Provenance]]:
    """Recomputed from the sample grain under a filter that cuts below `grain`."""
    columns: List[str] = []
    provenance: Dict[str, Provenance] = {}

    for col in measure.additive:
        columns.append(f"COALESCE(SUM({alias}.{col}), 0)::bigint AS {col}")
        provenance[col] = Provenance.AGGREGATED

    for col in measure.means:
        if col in measure.empty_columns:
            columns.append(f"NULL::double precision AS {col}")
            provenance[col] = Provenance.EMPTY
        elif measure.weight:
            # A count-weighted mean of pre-aggregated means. Defensible, and flagged
            # as approximate so the UI can mark it.
            columns.append(
                f"SUM({alias}.{col} * {alias}.{measure.weight})"
                f" / NULLIF(SUM({alias}.{measure.weight}), 0) AS {col}"
            )
            provenance[col] = Provenance.APPROXIMATE
        else:
            columns.append(f"AVG({alias}.{col}) AS {col}")
            provenance[col] = Provenance.APPROXIMATE

    for col in measure.percentiles:
        # Percentiles of a union are not a function of the parts' percentiles.
        columns.append(f"NULL::double precision AS {col}")
        provenance[col] = (
            Provenance.EMPTY if col in measure.empty_columns else Provenance.UNAVAILABLE
        )

    for col in measure.extremes:
        columns.append(f"MAX({alias}.{col}) AS {col}")
        provenance[col] = Provenance.AGGREGATED

    return columns, provenance


# -- assembly ----------------------------------------------------------------


def build(spec: QuerySpec, paginate: bool = True) -> Tuple[str, List[Any], Dict[str, Provenance], List[str]]:
    measure = MEASURES[spec.measure]
    grain = spec.grain
    gkey = GRAIN_KEY[grain]
    params = Params()
    notes: List[str] = []

    cuts = spec.filters.cuts_below(grain)
    aggregatable = "sample" in measure.tables

    ctes = [scope_cte(spec.filters, params)]

    if not cuts:
        source_table = measure.table_for(grain)
        dim_conditions, dim_joins, dim_notes = dimension_filters(
            measure, spec.filters, params, "m"
        )
        notes.extend(dim_notes)
        value_cols, provenance = value_columns_exact(measure, "m")

        ctes.append(f"keys AS (SELECT DISTINCT {gkey} FROM scope)")
        from_sql = f"FROM {source_table} m JOIN keys k ON k.{gkey} = m.{gkey}"
        dim_select = [f"m.{d}" for d in measure.dims]
        where_sql = f"WHERE {' AND '.join(dim_conditions)}" if dim_conditions else ""
        group_sql = ""
        extra_joins = dim_joins
        outer_alias = "m"

    elif aggregatable:
        source_table = measure.table_for("sample")
        dim_conditions, dim_joins, dim_notes = dimension_filters(
            measure, spec.filters, params, "m"
        )
        notes.extend(dim_notes)
        value_cols, provenance = value_columns_aggregated(measure, "m")
        agg_dims = [f"m.{d}" for d in measure.dims]
        where_sql = f"WHERE {' AND '.join(dim_conditions)}" if dim_conditions else ""
        group_cols = [f"sc.{gkey}"] + agg_dims

        ctes.append(
            f"""agg AS (
    SELECT sc.{gkey} AS {gkey}{''.join(', ' + d for d in agg_dims)},
           {', '.join(value_cols)}
    FROM {source_table} m
    JOIN scope sc ON sc.sample_id = m.sample_id
    {' '.join(dim_joins)}
    {where_sql}
    GROUP BY {', '.join(group_cols)}
)"""
        )
        notes.append(
            f"Recomputed from the sample grain because the filter selects part of a "
            f"{grain}. Counts are exact sums; percentiles are not recoverable from "
            f"pre-aggregated data and are returned as null."
        )
        from_sql = "FROM agg m"
        dim_select = [f"m.{d}" for d in measure.dims]
        value_cols = [f"m.{c}" for c in measure.value_columns]
        where_sql = ""
        group_sql = ""
        extra_joins = []
        outer_alias = "m"

    else:
        # clonesize lives only on study_summary -- there is no finer table to roll up
        # from, so a filter that cuts into the study makes it unanswerable.
        source_table = measure.table_for(grain)
        provenance = {c: Provenance.UNAVAILABLE for c in measure.value_columns}
        value_cols = [f"NULL::double precision AS {c}" for c in measure.value_columns]
        notes.append(
            f"Measure '{measure.name}' is stored only at study grain and cannot be "
            f"recomputed for a subset of a study. Values are returned as null."
        )
        ctes.append(f"keys AS (SELECT DISTINCT {gkey} FROM scope)")
        from_sql = f"FROM {source_table} m JOIN keys k ON k.{gkey} = m.{gkey}"
        dim_select = [f"m.{d}" for d in measure.dims]
        where_sql = ""
        group_sql = ""
        extra_joins = []
        outer_alias = "m"

    crumb_cols, crumb_joins = breadcrumb(grain, outer_alias)
    name_joins, name_cols = dimension_joins(measure, outer_alias)

    select_cols = crumb_cols + dim_select + name_cols + value_cols
    if paginate:
        select_cols = select_cols + ["COUNT(*) OVER () AS __total"]

    order_sql = _order_by(spec, measure, grain)
    limit_sql = ""
    if paginate:
        offset = (spec.page - 1) * spec.page_size
        limit_sql = f"LIMIT {params.add(spec.page_size)} OFFSET {params.add(offset)}"

    sql = f"""WITH {', '.join(ctes)}
SELECT {', '.join(select_cols)}
{from_sql}
{' '.join(crumb_joins)}
{' '.join(extra_joins)}
{' '.join(name_joins)}
{where_sql}
{group_sql}
{order_sql}
{limit_sql}"""

    return sql, params.values, provenance, notes


def _order_by(spec: QuerySpec, measure: Measure, grain: str) -> str:
    if spec.sort is not None:
        direction = "DESC" if spec.sort.descending else "ASC"
        return f"ORDER BY m.{spec.sort.column} {direction} NULLS LAST"

    # A stable, useful default: biggest first for count measures, then identity.
    default_sort: Optional[str] = None
    if measure.additive:
        default_sort = measure.additive[0]
    parts = []
    if default_sort:
        parts.append(f"m.{default_sort} DESC NULLS LAST")
    parts.append(f"m.{GRAIN_KEY[grain]}")
    parts.extend(f"m.{d}" for d in measure.dims)
    return f"ORDER BY {', '.join(parts)}"


def output_columns(spec: QuerySpec) -> List[str]:
    """Column order of the result rows, for CSV headers and table rendering."""
    measure = MEASURES[spec.measure]
    columns = list(BREADCRUMB_COLUMNS[spec.grain])
    for dim in measure.dims:
        columns.append(dim)
        lookup = DIMENSIONS.get(dim)
        if lookup and lookup.is_lookup:
            columns.append(lookup.name_column)
            if dim == "vj_allele_id":
                columns.extend(["vj_allele_segment", "vj_allele_gene"])
    columns.extend(measure.value_columns)
    return columns
