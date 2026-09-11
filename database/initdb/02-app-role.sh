#!/usr/bin/env bash
# Creates `abcd_app`, the least-privilege role the web app connects as.
#
# The planned interface (dashboards + query/download) only reads, so this role
# gets SELECT on the tables and views in public/raw/ui and nothing more. Use
# the `postgres` superuser for migrations and admin work instead.
set -euo pipefail

echo "[02-app-role] creating role 'abcd_app'..."

psql --username "${POSTGRES_USER}" --dbname abcd \
     --set ON_ERROR_STOP=on --no-psqlrc \
     --set app_password="${ABCD_APP_PASSWORD}" <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'abcd_app') THEN
    CREATE ROLE abcd_app LOGIN;
  END IF;
END
$$;

ALTER ROLE abcd_app WITH PASSWORD :'app_password';

GRANT CONNECT ON DATABASE abcd TO abcd_app;

-- Tables and views that exist right now.
GRANT USAGE ON SCHEMA public, raw, ui TO abcd_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public, raw, ui TO abcd_app;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public, raw, ui TO abcd_app;

-- ...and anything created later by postgres in those schemas.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public, raw, ui
  GRANT SELECT ON TABLES TO abcd_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public, raw, ui
  GRANT SELECT ON SEQUENCES TO abcd_app;

-- Postgres 15+ no longer grants CREATE on public by default, but be explicit.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL

echo "[02-app-role] done."
