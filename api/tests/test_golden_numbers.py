"""Contract tests against the live dataset.

Every figure here was read out of the database directly, so a regression in the
query builder shows up as a wrong number rather than as a passing test.
"""
import pytest

STUDY_BCRS = 18_713
CHAIN_TOTALS = {"IGH": 18_713, "IGK": 11_727, "IGL": 7_524}
SEGMENT_COUNTS = {"IGHV": 188, "IGKV": 65, "IGLV": 63, "IGHJ": 13, "IGKJ": 8, "IGLJ": 4}


async def test_health_row_counts(client):
    body = (await client.get("/health")).json()
    assert body["status"] == "ok"
    assert body["database"] == {
        "studies": 1,
        "subjects": 6,
        "samples": 8,
        "celltypes": 36,
        "alleles": 341,
        "bcrs": STUDY_BCRS,
        "connected_as": "abcd_app",
    }


async def test_connects_as_the_read_only_role(client):
    """The API must never hold write privileges -- the guarantee is at the DB level."""
    body = (await client.get("/health")).json()
    assert body["database"]["connected_as"] == "abcd_app"


async def test_chain_totals_at_study_grain(client):
    body = (await client.get("/stats/chain", params={"grain": "study"})).json()
    totals = {r["chain"]: r["count_chain"] for r in body["rows"]}
    assert totals == CHAIN_TOTALS
    assert body["provenance"]["count_chain"] == "exact"


async def test_allele_segment_breakdown(client):
    body = (await client.get("/meta/alleles", params={"limit": 5000})).json()
    counts = {}
    for row in body:
        counts[row["vj_allele_segment"]] = counts.get(row["vj_allele_segment"], 0) + 1
    assert counts == SEGMENT_COUNTS
    assert len(body) == 341


async def test_no_d_segment_alleles(client):
    """The table is called vj_allele and it means it -- V and J only."""
    body = (await client.get("/meta/alleles", params={"limit": 5000})).json()
    assert not [r for r in body if r["vj_allele_segment"] == "IGHD"]


@pytest.mark.parametrize(
    "measure,column",
    [
        ("summary", "count_bcrs"),
        ("chain", "count_chain"),
        ("celltype", "count_bcrs"),
        ("allele", "count_vj_allele"),
        ("allele_celltype", "count_vj_allele"),
        ("chain_celltype", "count_chain"),
    ],
)
async def test_rollup_consistency(client, measure, column):
    """Summing the sample grain must equal the stored study row.

    This is the assumption the whole `aggregated` provenance path rests on -- if it
    ever stops holding, filtered dashboards start lying.
    """
    study = (await client.get(f"/stats/{measure}", params={"grain": "study", "page_size": 5000})).json()
    sample = (await client.get(f"/stats/{measure}", params={"grain": "sample", "page_size": 5000})).json()
    assert sum(r[column] for r in study["rows"]) == sum(r[column] for r in sample["rows"])
