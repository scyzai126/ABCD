# ABCD database — local setup

The ABCD B-cell database runs as a Postgres 16 container defined in
[`../docker-compose.yml`](../docker-compose.yml). `abcd_test.dump` is restored
into it automatically on first boot.

## Requirements

Docker. This machine uses **Colima** (a lightweight CLI-only Docker engine) rather
than Docker Desktop, because Homebrew's `docker-desktop` cask was unparseable by
Homebrew 6.0.22 at setup time. Already installed here; to reproduce elsewhere:

```bash
brew install colima docker docker-compose
colima start --cpu 2 --memory 4 --disk 20
```

`docker-compose` is a CLI plugin, so `~/.docker/config.json` needs:

```json
{ "cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"] }
```

The VM does not survive a reboot on its own. Either run `colima start` after
logging in, or `brew services start colima` to have it come back automatically
(the `db` container is `restart: unless-stopped`, so it follows the VM up).
`colima stop` shuts the whole engine down; `colima status` shows its state.

Docker Desktop would also work if the cask is fixed later — nothing in
`docker-compose.yml` depends on Colima.

## Commands

Run from the **project root** (`/Users/unit4995/Desktop/ABCD`):

```bash
cp .env.example .env         # first time only, then fill in passwords
docker compose up -d         # start; restores the dump on first boot
docker compose logs -f db    # watch the pg_restore output
docker compose ps            # should read "healthy"
docker compose stop          # stop, keeping data
docker compose down -v && docker compose up -d   # wipe and re-restore from the dump
```

## Connecting

| Role | Use for | Connection string |
| --- | --- | --- |
| `abcd_app` | the web app (read-only) | `postgresql://abcd_app:$ABCD_APP_PASSWORD@localhost:5432/abcd` |
| `postgres` | admin, migrations | `postgresql://postgres:$POSTGRES_PASSWORD@localhost:5432/abcd` |

Once the app runs as a service in the same compose file, the host becomes `db`
instead of `localhost`.

A shell on the database:

```bash
docker compose exec db psql -U postgres -d abcd
```

For a native `psql` on your PATH: `brew install libpq` (then add its `bin` to PATH).

## Browsing the data in pgAdmin

pgAdmin 4 is installed at `/Applications/pgAdmin 4.app` (`brew install --cask pgadmin4`).

First run asks you to set a **master password** — that is pgAdmin's own local
password store, unrelated to Postgres. Then load the two pre-built connections
instead of typing host/port by hand:

> Object Explorer -> right-click **Servers** -> *Register* -> *Import Server*
> (or **Tools -> Import/Export Servers**), and pick
> `database/pgadmin-servers.json`.

That registers:

- **ABCD (admin)** — user `postgres`, for schema browsing and DDL
- **ABCD (app, read-only)** — user `abcd_app`, to check what the web app can see

Passwords are in `.env`; tick *Save password* on first connect. The data lives
under `Servers -> ABCD -> abcd -> Databases -> abcd -> Schemas`, with tables under
`public` and the app-facing views under `ui`. Query Tool is *Tools -> Query Tool*
(or the shortcut on a selected database).

pgAdmin talks to the container over the published port `localhost:5432`, so
Colima and the `db` container must be running (`docker compose ps`).

## What's inside

Schemas `public`, `raw`, `ui`. Roughly 23 data tables — `study`, `subject`,
`sample`, `vj_allele`, `annotated_celltype` and the `*_summary` rollups — plus a
layer of reporting views (`study_overview_view`,
`sample_celltype_statistics_view`, `sample_chain_summary_view`, …). Column-level
detail is in [`ABCD_database_tables.md`](ABCD_database_tables.md) and
[`ABCD_database_schema.png`](../document/ABCD_database_schema.png).

## Two gotchas worth remembering

- **Use the Debian image, not `postgres:16-alpine`.** The dump's database was
  created with `LOCALE_PROVIDER = libc, LOCALE = 'en_US.UTF-8'`, which musl libc
  (alpine) does not provide.
- **The restore omits `--create` / `--clean`.** The entrypoint has already
  created `abcd` and `pg_restore` is connected to it, so those flags would fail.
  Re-provision by dropping the volume (`docker compose down -v`) instead.

The dump itself was produced by `pg_dump -Fc` on PostgreSQL 16.15 (Ubuntu); it
needs no extensions and contains no functions or triggers.
