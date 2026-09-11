"""The rules that keep filtered dashboards honest."""


async def test_unfiltered_percentiles_are_exact(client):
    body = (await client.get("/stats/chain", params={"grain": "study"})).json()
    assert body["provenance"]["cdr3_median"] == "exact"
    assert all(r["cdr3_median"] is not None for r in body["rows"])


async def test_filtered_percentiles_are_null_not_wrong(client):
    """A sample filter cuts into the study, so study-grain percentiles cannot be
    recovered. They must come back null -- never as a plausible average."""
    body = (
        await client.get("/stats/chain", params={"grain": "study", "sample_id": 1})
    ).json()
    assert body["provenance"]["cdr3_median"] == "unavailable"
    assert all(r["cdr3_median"] is None for r in body["rows"])
    for percentile in ("cdr3_p05", "cdr3_p25", "cdr3_p75", "cdr3_p95"):
        assert body["provenance"][percentile] == "unavailable"


async def test_filtered_counts_stay_exact_sums(client):
    """Counts are additive, so they survive the same filter that kills percentiles."""
    body = (
        await client.get("/stats/chain", params={"grain": "study", "sample_id": 1})
    ).json()
    totals = {r["chain"]: r["count_chain"] for r in body["rows"]}
    assert totals == {"IGH": 1862, "IGK": 1096, "IGL": 814}
    assert body["provenance"]["count_chain"] == "aggregated"


async def test_filtered_mean_is_flagged_approximate(client):
    body = (
        await client.get("/stats/chain", params={"grain": "study", "sample_id": 1})
    ).json()
    assert body["provenance"]["cdr3_mean"] == "approximate"
    assert all(r["cdr3_mean"] is not None for r in body["rows"])


async def test_mutfreq_is_reported_empty_everywhere(client):
    for measure in ("chain", "chain_celltype"):
        body = (await client.get(f"/stats/{measure}", params={"grain": "study"})).json()
        for column in ("mutfreq_mean", "mutfreq_median", "mutfreq_p05", "mutfreq_p95"):
            assert body["provenance"][column] == "empty", (measure, column)


async def test_clonesize_cannot_be_recomputed_for_a_subset(client):
    """clonesize_* exists only on study_summary; there is no finer table to roll up."""
    body = (
        await client.get("/stats/clonesize", params={"grain": "study", "sample_id": 1})
    ).json()
    assert body["provenance"]["largest_clonesize"] == "unavailable"
    assert body["rows"][0]["largest_clonesize"] is None
    assert any("cannot be recomputed" in n for n in body["notes"])


async def test_clonesize_rejects_finer_grains(client):
    response = await client.get("/stats/clonesize", params={"grain": "sample"})
    assert response.status_code == 422


async def test_inapplicable_filter_is_reported_not_silently_dropped(client):
    """Filtering by chain on a measure with no chain dimension must say so."""
    body = (
        await client.get("/stats/celltype", params={"grain": "study", "chain": "IGH"})
    ).json()
    assert any("Chain filter not applied" in n for n in body["notes"])


async def test_isotype_breakdown_unavailable_under_a_chain_filter(client):
    """There is no isotype-by-chain table, so the panel must refuse rather than
    show unfiltered numbers."""
    body = (await client.get("/dashboard", params={"level": "project", "chain": "IGH"})).json()
    isotype = body["breakdowns"]["isotype"]
    assert isotype["provenance"] == "unavailable"
    assert isotype["rows"] == []
