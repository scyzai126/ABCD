"""Runtime facet availability.

The design decks facet the dashboards by organism, disease, tissue, exposure
material, sex, age and time collected. None of those columns hold a value in the
current dump. Rather than hard-code that absence -- which would have to be undone
when the real dataset lands -- availability is *measured*: each declared facet is
probed for distinct values, and the UI hides the ones that come back empty.

Populate the columns upstream and the filters appear on their own.
"""
import asyncio
import logging
from typing import Dict, List, Optional

from . import db
from .models import FacetAvailability, FacetValue
from .registry import DIMENSION_FACETS, Facet, METADATA_FACETS

log = logging.getLogger(__name__)

#: Above this many distinct values a facet reports its count but not its values;
#: the client fetches them from the dedicated /meta endpoint instead.
INLINE_VALUE_LIMIT = 250

_cache: Optional[List[FacetAvailability]] = None


async def _categorical(facet: Facet) -> FacetAvailability:
    rows = await db.fetch(
        f"""
        SELECT {facet.column} AS value, count(*) AS n
        FROM {facet.level}
        WHERE {facet.column} IS NOT NULL
        GROUP BY 1
        ORDER BY n DESC, 1
        LIMIT {INLINE_VALUE_LIMIT + 1}
        """
    )
    values = [
        FacetValue(value=r["value"], label=str(r["value"]), count=r["n"]) for r in rows
    ]
    distinct = await db.fetchval(
        f"SELECT count(DISTINCT {facet.column}) FROM {facet.level}"
    )
    return FacetAvailability(
        field=facet.field,
        label=facet.label,
        level=facet.level,
        kind=facet.kind,
        available=distinct > 0,
        distinct_count=distinct,
        derived=facet.derived,
        note=facet.note or _empty_note(distinct, facet),
        values=values[:INLINE_VALUE_LIMIT] if distinct <= INLINE_VALUE_LIMIT else [],
    )


async def _ranged(facet: Facet) -> FacetAvailability:
    row = await db.fetchrow(
        f"""
        SELECT min({facet.column}) AS lo, max({facet.column}) AS hi,
               count({facet.column}) AS n
        FROM {facet.level}
        """
    )
    lo, hi, n = row["lo"], row["hi"], row["n"]
    to_float = (
        (lambda v: v.timestamp() if v is not None else None)
        if facet.kind == "temporal"
        else (lambda v: float(v) if v is not None else None)
    )
    return FacetAvailability(
        field=facet.field,
        label=facet.label,
        level=facet.level,
        kind=facet.kind,
        available=n > 0,
        distinct_count=n,
        derived=facet.derived,
        note=facet.note or _empty_note(n, facet),
        min=to_float(lo),
        max=to_float(hi),
    )


def _empty_note(count: int, facet: Facet) -> str:
    if count:
        return ""
    return (
        f"No values in this dataset. The {facet.column} column on {facet.level} is "
        f"not populated by the current pipeline output; this filter will appear "
        f"automatically once it is."
    )


async def _chain_facet() -> FacetAvailability:
    rows = await db.fetch(
        """
        SELECT chain AS value, sum(count_chain)::bigint AS n
        FROM study_chain_summary GROUP BY 1 ORDER BY n DESC
        """
    )
    return FacetAvailability(
        field="chain",
        label="Chain",
        level="sample",
        kind="categorical",
        available=bool(rows),
        distinct_count=len(rows),
        values=[FacetValue(value=r["value"], label=r["value"], count=r["n"]) for r in rows],
    )


async def _celltype_facet() -> FacetAvailability:
    rows = await db.fetch(
        """
        SELECT ct.annotated_celltype_id AS value, ct.annotated_celltype_name AS label,
               COALESCE(sac.count_bcrs, 0) AS n
        FROM annotated_celltype ct
        LEFT JOIN study_annotated_celltype sac
               ON sac.annotated_celltype_id = ct.annotated_celltype_id
        ORDER BY n DESC, label
        """
    )
    return FacetAvailability(
        field="celltype_id",
        label="Cell type",
        level="sample",
        kind="categorical",
        available=bool(rows),
        distinct_count=len(rows),
        values=[
            FacetValue(value=r["value"], label=r["label"], count=r["n"]) for r in rows
        ],
    )


async def _allele_facets() -> List[FacetAvailability]:
    total = await db.fetchval("SELECT count(*) FROM vj_allele")
    segments = await db.fetch(
        """
        SELECT substring(vj_allele_name from '^IG[HKL][VJ]') AS value, count(*) AS n
        FROM vj_allele GROUP BY 1 ORDER BY n DESC
        """
    )
    genes = await db.fetchval(
        "SELECT count(DISTINCT split_part(vj_allele_name, '*', 1)) FROM vj_allele"
    )
    return [
        FacetAvailability(
            field="allele_id",
            label="V/J allele",
            level="sample",
            kind="categorical",
            available=total > 0,
            distinct_count=total,
            note="Too many values to inline; fetch the list from /api/v1/meta/alleles.",
        ),
        FacetAvailability(
            field="allele_segment",
            label="Allele segment",
            level="sample",
            kind="categorical",
            available=bool(segments),
            distinct_count=len(segments),
            derived=True,
            note="Derived from the allele name. V and J segments only -- the dataset has no D segments.",
            values=[
                FacetValue(value=r["value"], label=r["value"], count=r["n"])
                for r in segments
            ],
        ),
        FacetAvailability(
            field="allele_gene",
            label="Allele gene",
            level="sample",
            kind="categorical",
            available=genes > 0,
            distinct_count=genes,
            derived=True,
            note="Derived from the allele name; fetch the list from /api/v1/meta/alleles.",
        ),
    ]


async def compute() -> List[FacetAvailability]:
    dimension = await asyncio.gather(_chain_facet(), _celltype_facet(), _allele_facets())
    result: List[FacetAvailability] = [dimension[0], dimension[1]] + dimension[2]

    for facet in METADATA_FACETS:
        if facet.kind == "categorical":
            result.append(await _categorical(facet))
        else:
            result.append(await _ranged(facet))
    return result


async def get(refresh: bool = False) -> List[FacetAvailability]:
    global _cache
    if _cache is None or refresh:
        _cache = await compute()
        available = sum(1 for f in _cache if f.available)
        log.info("facet availability: %s of %s populated", available, len(_cache))
    return _cache


async def availability_map(refresh: bool = False) -> Dict[str, bool]:
    return {f.field: f.available for f in await get(refresh)}


def clear_cache() -> None:
    global _cache
    _cache = None


#: Declared so the module is importable without touching the registry ordering.
ALL_FACETS = DIMENSION_FACETS + METADATA_FACETS
