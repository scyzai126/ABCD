"""Dashboard assembly for the project-level and study-level pages.

The decks require that "by restricting specific feature parameters, the aggregate
summary at the Subject/Sample/BCR level can be dynamically recalculated". Two things
make that honest here:

1. Every breakdown is served from the *finest face of the cube that covers the
   active dimension filters*. Filter by chain and the cell-type breakdown switches
   from `celltype` (count_bcrs) to `chain_celltype` (count_chain), because the
   former cannot be split by chain. Where the cube genuinely cannot answer -- an
   isotype breakdown under a chain filter -- the panel reports `unavailable` rather
   than quietly showing unfiltered numbers.
2. Provenance from the query builder is carried through to every tile and chart.

Result sets here are small (the widest face is 4,880 rows), so the per-study rows
come back unpaginated and the cross-study rollup happens in Python. That keeps a
single SQL path shared with /stats and /query.
"""
from typing import Any, Dict, List, Optional, Tuple

from . import db
from .models import Breakdown, Dashboard, Filters, Kpi, Provenance, QuerySpec
from .query import build, scope_cte, Params

#: Worst-to-best, for combining provenance across several columns.
_SEVERITY = {
    Provenance.EXACT: 0,
    Provenance.AGGREGATED: 1,
    Provenance.APPROXIMATE: 2,
    Provenance.EMPTY: 3,
    Provenance.UNAVAILABLE: 4,
}

TOP_CELLTYPES = 10
TOP_ALLELES = 20


def _worst(*values: Provenance) -> Provenance:
    return max(values, key=lambda p: _SEVERITY[p]) if values else Provenance.EXACT


async def _rows(
    measure: str, grain: str, filters: Filters
) -> Tuple[List[Dict[str, Any]], Dict[str, Provenance], List[str]]:
    spec = QuerySpec(measure=measure, grain=grain, filters=filters)
    sql, params, provenance, notes = build(spec, paginate=False)
    records = await db.fetch(sql, *params)
    return [dict(r) for r in records], provenance, notes


async def _scope_counts(filters: Filters) -> Dict[str, int]:
    params = Params()
    sql = f"""WITH {scope_cte(filters, params)}
SELECT count(DISTINCT study_id) AS studies,
       count(DISTINCT subject_id) AS subjects,
       count(DISTINCT sample_id) AS samples
FROM scope"""
    row = await db.fetchrow(sql, *params.values)
    return dict(row) if row else {"studies": 0, "subjects": 0, "samples": 0}


def _sum_by(rows: List[Dict[str, Any]], key: str, value: str) -> Dict[Any, int]:
    out: Dict[Any, int] = {}
    for row in rows:
        amount = row.get(value)
        if amount is None:
            continue
        out[row[key]] = out.get(row[key], 0) + amount
    return out


# -- breakdown sources -------------------------------------------------------


def _chain_measure(filters: Filters) -> str:
    return "chain_celltype" if filters.celltype_id else "chain"


def _celltype_measure(filters: Filters) -> str:
    return "chain_celltype" if filters.chain else "celltype"


def _allele_measure(filters: Filters) -> str:
    return "allele_celltype" if filters.celltype_id else "allele"


async def _chain_breakdown(filters: Filters, grain: str) -> Breakdown:
    measure = _chain_measure(filters)
    rows, provenance, _ = await _rows(measure, grain, filters)
    totals = _sum_by(rows, "chain", "count_chain")
    return Breakdown(
        key="chain",
        label="BCR chains by locus",
        source=measure,
        provenance=provenance.get("count_chain", Provenance.EXACT),
        rows=[
            {"chain": chain, "count": count}
            for chain, count in sorted(totals.items(), key=lambda kv: -kv[1])
        ],
    )


async def _celltype_breakdown(filters: Filters, grain: str) -> Breakdown:
    measure = _celltype_measure(filters)
    value_column = "count_chain" if measure == "chain_celltype" else "count_bcrs"
    rows, provenance, _ = await _rows(measure, grain, filters)

    names = {r["annotated_celltype_id"]: r.get("annotated_celltype_name") for r in rows}
    totals = _sum_by(rows, "annotated_celltype_id", value_column)
    ordered = sorted(totals.items(), key=lambda kv: -kv[1])

    # 20 of the 36 cell types carry 5 or fewer BCRs -- a full axis is unreadable.
    head = ordered[:TOP_CELLTYPES]
    tail = ordered[TOP_CELLTYPES:]
    result = [
        {
            "annotated_celltype_id": celltype_id,
            "annotated_celltype_name": names.get(celltype_id) or f"#{celltype_id}",
            "count": count,
        }
        for celltype_id, count in head
    ]
    if tail:
        result.append(
            {
                "annotated_celltype_id": None,
                "annotated_celltype_name": f"Other ({len(tail)} cell types)",
                "count": sum(count for _, count in tail),
            }
        )
    note = "" if measure == "celltype" else (
        "Counts are chain observations, not BCRs, because a chain filter is active."
    )
    return Breakdown(
        key="celltype",
        label="BCRs by cell type",
        source=measure,
        provenance=provenance.get(value_column, Provenance.EXACT),
        rows=result,
        note=note,
    )


async def _allele_breakdown(filters: Filters, grain: str) -> Breakdown:
    measure = _allele_measure(filters)
    rows, provenance, _ = await _rows(measure, grain, filters)
    names = {r["vj_allele_id"]: r.get("vj_allele_name") for r in rows}
    segments = {r["vj_allele_id"]: r.get("vj_allele_segment") for r in rows}
    totals = _sum_by(rows, "vj_allele_id", "count_vj_allele")
    ordered = sorted(totals.items(), key=lambda kv: -kv[1])[:TOP_ALLELES]
    return Breakdown(
        key="allele",
        label=f"Top {TOP_ALLELES} V/J alleles",
        source=measure,
        provenance=provenance.get("count_vj_allele", Provenance.EXACT),
        rows=[
            {
                "vj_allele_id": allele_id,
                "vj_allele_name": names.get(allele_id) or f"#{allele_id}",
                "vj_allele_segment": segments.get(allele_id),
                "count": count,
            }
            for allele_id, count in ordered
        ],
    )


async def _isotype_breakdown(filters: Filters, grain: str) -> Breakdown:
    isotypes = [
        ("count_igm", "IgM"),
        ("count_igd", "IgD"),
        ("count_iga", "IgA"),
        ("count_igg", "IgG"),
        ("count_ige", "IgE"),
    ]
    if filters.chain:
        # No isotype x chain table exists anywhere in the cube.
        return Breakdown(
            key="isotype",
            label="Isotype distribution",
            source="unavailable",
            provenance=Provenance.UNAVAILABLE,
            rows=[],
            note=(
                "Isotype counts cannot be split by chain -- the database has no "
                "isotype-by-chain table. Clear the chain filter to see this breakdown."
            ),
        )

    measure = "celltype" if filters.celltype_id else "summary"
    rows, provenance, _ = await _rows(measure, grain, filters)
    totals = {
        label: sum((row.get(column) or 0) for row in rows) for column, label in isotypes
    }
    provenances = [provenance.get(column, Provenance.EXACT) for column, _ in isotypes]
    return Breakdown(
        key="isotype",
        label="Isotype distribution",
        source=measure,
        provenance=_worst(*provenances),
        rows=[{"isotype": label, "count": totals[label]} for _, label in isotypes],
        note="IgE is absent from almost every record in this dataset.",
    )


async def _cdr3_breakdown(filters: Filters, grain: str, studies_in_scope: int) -> Breakdown:
    measure = _chain_measure(filters)
    rows, provenance, _ = await _rows(measure, grain, filters)

    percentile_provenance = provenance.get("cdr3_median", Provenance.EXACT)
    note = ""
    if studies_in_scope > 1:
        # Percentiles of a union are not a function of the parts' percentiles.
        percentile_provenance = Provenance.UNAVAILABLE
        note = (
            "CDR3 percentiles cannot be combined across studies. Select a single "
            "study to see the distribution."
        )

    by_chain: Dict[str, Dict[str, Any]] = {}
    weights: Dict[str, int] = {}
    for row in rows:
        chain = row.get("chain")
        count = row.get("count_chain") or 0
        if chain is None:
            continue
        entry = by_chain.setdefault(
            chain,
            {"chain": chain, "count": 0, "cdr3_mean": None,
             "p05": None, "p25": None, "median": None, "p75": None, "p95": None},
        )
        entry["count"] += count
        weights[chain] = weights.get(chain, 0) + count

    if percentile_provenance is not Provenance.UNAVAILABLE:
        for row in rows:
            chain = row.get("chain")
            if chain in by_chain:
                by_chain[chain].update(
                    {
                        "cdr3_mean": row.get("cdr3_mean"),
                        "p05": row.get("cdr3_p05"),
                        "p25": row.get("cdr3_p25"),
                        "median": row.get("cdr3_median"),
                        "p75": row.get("cdr3_p75"),
                        "p95": row.get("cdr3_p95"),
                    }
                )
    else:
        # The mean is still count-weightable even when percentiles are not.
        sums: Dict[str, float] = {}
        for row in rows:
            chain, mean, count = row.get("chain"), row.get("cdr3_mean"), row.get("count_chain") or 0
            if chain in by_chain and mean is not None:
                sums[chain] = sums.get(chain, 0.0) + mean * count
        for chain, entry in by_chain.items():
            if weights.get(chain):
                entry["cdr3_mean"] = sums.get(chain, 0.0) / weights[chain]

    return Breakdown(
        key="cdr3",
        label="CDR3 length by chain",
        source=measure,
        provenance=percentile_provenance,
        rows=sorted(by_chain.values(), key=lambda r: -r["count"]),
        note=note,
    )


async def _mutfreq_breakdown() -> Breakdown:
    return Breakdown(
        key="mutfreq",
        label="Somatic hypermutation frequency",
        source="chain",
        provenance=Provenance.EMPTY,
        rows=[],
        note=(
            "Not computed in this dataset. All six mutfreq_* columns are empty across "
            "every chain-summary table, while cdr3_* in the same rows is populated -- "
            "the mutation-frequency step appears not to have run upstream."
        ),
    )


# -- KPIs --------------------------------------------------------------------


async def _kpis(filters: Filters, grain: str, counts: Dict[str, int]) -> List[Kpi]:
    kpis: List[Kpi] = [
        Kpi(key="studies", label="Studies", value=counts["studies"]),
        Kpi(key="subjects", label="Subjects", value=counts["subjects"]),
        Kpi(key="samples", label="Samples", value=counts["samples"]),
    ]

    if filters.chain:
        rows, provenance, _ = await _rows(_chain_measure(filters), grain, filters)
        kpis.append(
            Kpi(
                key="bcrs",
                label="Chains (filtered)",
                value=sum((r.get("count_chain") or 0) for r in rows),
                provenance=provenance.get("count_chain", Provenance.EXACT),
                note="A chain filter is active, so this counts chain observations rather than BCRs.",
            )
        )
    else:
        measure = "celltype" if filters.celltype_id else "summary"
        rows, provenance, _ = await _rows(measure, grain, filters)
        kpis.append(
            Kpi(
                key="bcrs",
                label="BCRs",
                value=sum((r.get("count_bcrs") or 0) for r in rows),
                provenance=provenance.get("count_bcrs", Provenance.EXACT),
            )
        )

    chain_rows, chain_provenance, _ = await _rows(_chain_measure(filters), grain, filters)
    chain_totals = _sum_by(chain_rows, "chain", "count_chain")
    chain_prov = chain_provenance.get("count_chain", Provenance.EXACT)
    kpis.append(
        Kpi(key="heavy_chains", label="Heavy chains", value=chain_totals.get("IGH", 0),
            provenance=chain_prov)
    )
    kpis.append(
        Kpi(
            key="light_chains",
            label="Light chains",
            value=chain_totals.get("IGK", 0) + chain_totals.get("IGL", 0),
            provenance=chain_prov,
            note="IGK + IGL",
        )
    )

    celltype_rows, _, _ = await _rows(_celltype_measure(filters), grain, filters)
    kpis.append(
        Kpi(
            key="celltypes",
            label="Cell types",
            value=len({r["annotated_celltype_id"] for r in celltype_rows}),
        )
    )

    allele_rows, _, _ = await _rows(_allele_measure(filters), grain, filters)
    kpis.append(
        Kpi(
            key="alleles",
            label="V/J alleles",
            value=len({r["vj_allele_id"] for r in allele_rows}),
        )
    )

    clone_rows, clone_provenance, _ = await _rows("clonesize", "study", filters)
    largest = [r.get("largest_clonesize") for r in clone_rows if r.get("largest_clonesize")]
    kpis.append(
        Kpi(
            key="largest_clonesize",
            label="Largest clone",
            value=max(largest) if largest else None,
            provenance=clone_provenance.get("largest_clonesize", Provenance.EXACT),
            note="Clone size percentiles are stored only at study grain.",
        )
    )
    return kpis


# -- entry point -------------------------------------------------------------


async def assemble(level: str, filters: Filters, study_id: Optional[int] = None) -> Dashboard:
    if level == "study":
        if study_id is None:
            raise ValueError("study_id is required when level='study'")
        filters = filters.model_copy(update={"study_id": [study_id]})

    grain = "study"
    counts = await _scope_counts(filters)

    breakdowns = {
        "chain": await _chain_breakdown(filters, grain),
        "celltype": await _celltype_breakdown(filters, grain),
        "isotype": await _isotype_breakdown(filters, grain),
        "cdr3": await _cdr3_breakdown(filters, grain, counts["studies"]),
        "allele": await _allele_breakdown(filters, grain),
        "mutfreq": await _mutfreq_breakdown(),
    }

    notes: List[str] = []
    if filters.cuts_below(grain):
        notes.append(
            "A filter selects part of a study, so counts were recomputed from the "
            "sample grain. Percentile statistics are not recoverable at this scope."
        )

    return Dashboard(
        level=level,
        study_id=study_id,
        filters=filters,
        kpis=await _kpis(filters, grain, counts),
        breakdowns=breakdowns,
        notes=notes,
    )
