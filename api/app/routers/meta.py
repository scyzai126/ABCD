"""Dimension lists and the facet availability report."""
from typing import List

from fastapi import APIRouter, Query

from .. import db, facets
from ..models import FacetAvailability

router = APIRouter(prefix="/meta", tags=["metadata"])


@router.get("/facets", response_model=List[FacetAvailability])
async def list_facets(refresh: bool = Query(False, description="Re-probe the database.")):
    """Which filters have data behind them.

    Every facet the design decks call for is declared. The ones whose columns are
    unpopulated report `available: false` with a note, so the UI can hide them and
    light them up automatically once the metadata is loaded.
    """
    return await facets.get(refresh=refresh)


@router.get("/chains")
async def list_chains():
    """The chain values present in the data.

    Read from the data rather than hard-coded: `chain` is a varchar with no check
    constraint, so the set is a property of the dataset, not of the schema.
    """
    rows = await db.fetch(
        """
        SELECT chain, sum(count_chain)::bigint AS count_chain
        FROM study_chain_summary GROUP BY chain ORDER BY count_chain DESC
        """
    )
    return [dict(r) for r in rows]


@router.get("/celltypes")
async def list_celltypes():
    """All annotated cell types, ranked by study-level BCR count."""
    rows = await db.fetch(
        """
        SELECT ct.annotated_celltype_id, ct.annotated_celltype_name,
               ct.annotated_celltype_ontology,
               COALESCE(sac.count_bcrs, 0) AS count_bcrs
        FROM annotated_celltype ct
        LEFT JOIN study_annotated_celltype sac
               ON sac.annotated_celltype_id = ct.annotated_celltype_id
        ORDER BY count_bcrs DESC, ct.annotated_celltype_name
        """
    )
    return [dict(r) for r in rows]


@router.get("/alleles")
async def list_alleles(
    segment: List[str] = Query(default_factory=list, description="Filter by IGHV, IGKJ, ..."),
    limit: int = Query(1000, ge=1, le=5000),
):
    """V/J alleles with their segment and gene parsed out of the IMGT name."""
    rows = await db.fetch(
        """
        SELECT a.vj_allele_id, a.vj_allele_name,
               substring(a.vj_allele_name from '^IG[HKL][VJ]') AS vj_allele_segment,
               split_part(a.vj_allele_name, '*', 1) AS vj_allele_gene,
               split_part(a.vj_allele_name, '*', 2) AS allele_number,
               COALESCE(sva.count_vj_allele, 0) AS count_vj_allele
        FROM vj_allele a
        LEFT JOIN study_vj_allele sva ON sva.vj_allele_id = a.vj_allele_id
        WHERE cardinality($1::text[]) = 0
           OR substring(a.vj_allele_name from '^IG[HKL][VJ]') = ANY($1)
        ORDER BY count_vj_allele DESC, a.vj_allele_name
        LIMIT $2
        """,
        [s.upper() for s in segment],
        limit,
    )
    return [dict(r) for r in rows]


@router.get("/measures")
async def list_measures():
    """The faces of the cube, and which grains each is stored at."""
    from ..registry import MEASURES

    return [
        {
            "name": m.name,
            "label": m.label,
            "grains": list(m.grains),
            "dimensions": list(m.dims),
            "additive_columns": list(m.additive),
            "mean_columns": list(m.means),
            "percentile_columns": list(m.percentiles),
            "empty_columns": list(m.empty_columns),
        }
        for m in MEASURES.values()
    ]
