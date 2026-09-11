# ABCD B-cell database portal

A read-only web portal over the ABCD B-cell receptor repertoire database: two
dashboards and a query/download page, built to the design in [`document/`](document/).

```
document/   the original design decks, pipeline diagram and schema
database/   Postgres 16 in Docker, restored from abcd_test.dump
api/        FastAPI, read-only, serves /api/v1
web/        React + Vite front end
```

## Running it

The database comes first; see [`database/README.md`](database/README.md) for the
Colima/Docker setup.

```bash
cp .env.example .env          # first time: fill in both passwords
docker compose up -d          # database only
docker compose ps             # should read "healthy"
```

**Everything in Docker** -- the portal on <http://localhost:8080>, the API on
<http://localhost:8000/docs>:

```bash
docker compose --profile app up -d --build
```

**Or run the API and front end locally** while the database stays in Docker:

```bash
cd api
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env          # paste the ABCD_APP_PASSWORD from ../.env
.venv/bin/uvicorn app.main:app --reload      # http://localhost:8000/docs

cd ../web
npm install && npm run dev                   # http://localhost:5173
```

The Vite dev server proxies `/api` to port 8000, so the browser sees one origin.

### Tests

```bash
cd api && .venv/bin/python -m pytest
```

These are contract tests against the running container: the numbers they assert
(18,713 BCRs; 18,713/11,727/7,524 chains; 341 alleles) were read out of the dump,
so a regression in the query builder shows up as a wrong number rather than a
passing test.

## What the data is, and what that means for the portal

The database holds **pre-aggregated** statistics -- three levels (study, subject,
sample) crossed with six faces (summary, chain, cell type, chain x cell type, V/J
allele, allele x cell type). There are no per-receptor rows anywhere, which shapes
the whole design:

**Counts are additive; percentiles are not.** Filter to one sample and a study-level
count can be recomputed by summing the sample level, exactly. A study-level CDR3
median cannot -- percentiles of a subset are not a function of the parts'
percentiles. Every number in an API response therefore carries a `provenance`:

| value | meaning |
| --- | --- |
| `exact` | read from the stored aggregate at the requested level |
| `aggregated` | additive counts summed up from the sample level |
| `approximate` | a count-weighted mean of pre-aggregated means |
| `unavailable` | not recoverable under this filter -- returned as null, never guessed |
| `empty` | the column exists but holds no values in this dataset |

The UI renders that provenance beside the figure it belongs to. This is what lets
the dashboards satisfy the decks' "dynamically recalculated" requirement without
ever showing a plausible-looking wrong number.

**Breakdowns are served from the finest face that covers the active filters.**
Filter by chain and the cell-type chart switches from `celltype` (BCR counts) to
`chain_celltype` (chain counts), because the former cannot be split by chain. Where
the cube genuinely cannot answer -- an isotype breakdown under a chain filter, since
no isotype-by-chain table exists -- the panel says so instead of showing unfiltered
numbers.

**Most metadata filters have nothing behind them yet.** The decks facet by organism,
disease, tissue, exposure material, sex, age and time collected. All 35 of those
columns are empty in the loaded dump, as are all 36 `mutfreq_*` columns. Rather than
hard-code that, `/api/v1/meta/facets` measures availability at runtime and the rail
hides what is empty. **Populate the columns upstream and the filters appear on their
own** -- no code change here. Cohort is currently only inferable from subject names
(`HC*` vs `SLE*`) and timepoint from the `_T1` suffix; neither is used as a filter,
because guessing from a name is not a metadata column.

## API

`/docs` carries the full generated reference. The shape:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/health` | connectivity and headline counts |
| `GET /api/v1/meta/facets` | which filters have data behind them |
| `GET /api/v1/meta/{chains,celltypes,alleles,measures}` | dimension lists |
| `GET /api/v1/{studies,subjects,samples}` | entity listings from the `ui` views |
| `GET /api/v1/dashboard` | KPIs and breakdowns for either dashboard |
| `GET /api/v1/stats/{measure}` | one face of the cube at any level |
| `GET`/`POST /api/v1/query` | preview a query |
| `GET /api/v1/query/export` | the same query as a CSV/TSV download |

Filters are uniform across every endpoint: `study_id`, `subject_id`, `sample_id`,
`chain`, `celltype_id`, `allele_id`, `allele_segment`, `allele_gene`, plus
`meta=field:value` for entity metadata.

Every table and column name the API can emit is declared in `api/app/registry.py`.
Request input selects entries from that allowlist; it never becomes an identifier.
That is what makes the planned natural-language query mode safe to add: it will
translate a question into the same `QuerySpec` these endpoints already validate,
gaining no SQL surface of its own.

Every exported row carries its study name, per the decks' data-standardization
requirement, and the file opens with comment lines recording the filters used and
any column whose values are not exact.

## Optional: keys and indexes

`database/migrations/001_keys_and_indexes.sql` adds the foreign keys the schema
diagram documents but the dump does not contain, plus indexes on the columns the
portal filters by. Nothing depends on it -- at the current size every query is
instant -- and it is meant for the full dataset. Run it as the superuser:

```bash
docker compose exec -T db psql -U postgres -d abcd < database/migrations/001_keys_and_indexes.sql
```
