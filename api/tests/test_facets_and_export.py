"""Facet gating and the download contract."""
import csv
import io

EMPTY_METADATA_FIELDS = {
    "organism", "strain", "biological_sex", "age", "ethnicity", "race",
    "disease_reported", "disease_stage", "exposure_process_reported",
    "exposure_material_reported", "batch", "tissue", "cell_type", "treatment",
    "molecule", "time_collected", "time_t0_event",
}
POPULATED_FIELDS = {"chain", "celltype_id", "allele_id", "allele_segment", "allele_gene"}


async def test_metadata_facets_report_unavailable(client):
    """The decks facet by these fields; none of them have data yet. The API must say
    so rather than offer a filter that silently matches nothing."""
    facets = {f["field"]: f for f in (await client.get("/meta/facets")).json()}
    for field in EMPTY_METADATA_FIELDS:
        assert facets[field]["available"] is False, field
        assert facets[field]["distinct_count"] == 0, field
        assert facets[field]["note"], f"{field} should explain why it is empty"


async def test_dimension_facets_are_available(client):
    facets = {f["field"]: f for f in (await client.get("/meta/facets")).json()}
    for field in POPULATED_FIELDS:
        assert facets[field]["available"] is True, field
    assert facets["chain"]["distinct_count"] == 3
    assert facets["celltype_id"]["distinct_count"] == 36
    assert facets["allele_id"]["distinct_count"] == 341
    assert facets["allele_segment"]["distinct_count"] == 6


async def test_unknown_metadata_filter_is_rejected(client):
    response = await client.get("/stats/summary", params={"meta": "not_a_field:x"})
    assert response.status_code == 422


async def test_malformed_metadata_filter_is_rejected(client):
    response = await client.get("/stats/summary", params={"meta": "missing-colon"})
    assert response.status_code == 422


async def test_export_tags_every_row_with_the_study(client):
    """The decks require exported records to carry the study they came from."""
    response = await client.get(
        "/query/export", params={"measure": "chain", "grain": "sample", "format": "csv"}
    )
    assert response.status_code == 200
    body = [line for line in response.text.splitlines() if not line.startswith("#")]
    rows = list(csv.DictReader(io.StringIO("\n".join(body))))
    assert rows
    assert all(row["study_name"] == "D5" for row in rows)
    assert all(row["sample_name"] for row in rows)


async def test_export_row_count_matches_the_json_total(client):
    params = {"measure": "allele", "grain": "sample"}
    total = (await client.get("/query", params={**params, "page_size": 1})).json()["total"]
    export = await client.get("/query/export", params={**params, "format": "csv"})
    data_lines = [
        line for line in export.text.splitlines() if line and not line.startswith("#")
    ]
    assert len(data_lines) - 1 == total == 1503


async def test_export_records_provenance_in_its_header(client):
    response = await client.get(
        "/query/export", params={"measure": "chain", "grain": "study", "format": "csv"}
    )
    comments = [l for l in response.text.splitlines() if l.startswith("#")]
    assert any("mutfreq_mean=empty" in l for l in comments)
    assert any("measure=chain" in l for l in comments)


async def test_tsv_export_is_tab_delimited(client):
    response = await client.get(
        "/query/export", params={"measure": "summary", "grain": "study", "format": "tsv"}
    )
    header = [l for l in response.text.splitlines() if not l.startswith("#")][0]
    assert "\t" in header and "," not in header


async def test_post_query_accepts_the_same_spec(client):
    """The shape a future natural-language mode will emit."""
    response = await client.post(
        "/query",
        json={
            "measure": "chain",
            "grain": "subject",
            "filters": {"chain": ["IGH"]},
            "page_size": 10,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 6
    assert {r["chain"] for r in body["rows"]} == {"IGH"}


async def test_post_query_rejects_an_unknown_measure(client):
    response = await client.post("/query", json={"measure": "drop_tables", "grain": "study"})
    assert response.status_code == 422
