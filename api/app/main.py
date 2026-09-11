"""ABCD B-cell database API.

A read-only REST surface over the pre-aggregated BCR cube, serving the three pages
described in the ABCD design decks: project-level dashboard, study-level dashboard,
and the query/download page.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db, facets
from .config import get_settings
from .routers import dashboards, entities, meta, query, stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("abcd")

DESCRIPTION = """
Read-only access to the ABCD B-cell database.

The database stores **pre-aggregated** repertoire statistics -- three grains
(study / subject / sample) crossed with six faces (summary, chain, cell type,
chain x cell type, V/J allele, allele x cell type). There are no per-BCR records.

Because the data is pre-aggregated, not every filter can be honoured by every
statistic. Responses carry a `provenance` field so a client never has to guess:

| value | meaning |
| --- | --- |
| `exact` | read from the stored aggregate row at the requested grain |
| `aggregated` | additive counts summed up from the sample grain |
| `approximate` | a count-weighted mean of pre-aggregated means |
| `unavailable` | percentiles under a filter that requires recomputation -- returned as null |
| `empty` | the column exists but holds no values in this dataset |
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await facets.get(refresh=True)
    yield
    await db.disconnect()


app = FastAPI(
    title="ABCD B-cell database API",
    version="1.0.0",
    description=DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
for router in (meta.router, entities.router, dashboards.router, stats.router, query.router):
    app.include_router(router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/health", tags=["metadata"])
async def health():
    """Connectivity plus the headline row counts, for a quick sanity check."""
    row = await db.fetchrow(
        """
        SELECT (SELECT count(*) FROM study) AS studies,
               (SELECT count(*) FROM subject) AS subjects,
               (SELECT count(*) FROM sample) AS samples,
               (SELECT count(*) FROM annotated_celltype) AS celltypes,
               (SELECT count(*) FROM vj_allele) AS alleles,
               (SELECT count_bcrs FROM study_summary ORDER BY study_id LIMIT 1) AS bcrs,
               current_user AS connected_as
        """
    )
    available = await facets.availability_map()
    return {
        "status": "ok",
        "database": dict(row),
        "facets": {
            "declared": len(available),
            "populated": sum(1 for v in available.values() if v),
        },
    }


@app.get("/", include_in_schema=False)
async def root():
    return {"name": "ABCD B-cell database API", "docs": "/docs", "api": API_PREFIX}
