#!/usr/bin/env bash
# Restores abcd_test.dump into the `abcd` database that the Postgres
# entrypoint has just created.
#
# No --create / --clean here on purpose: the database already exists and we are
# connected to it, so those flags would fail. To re-provision from scratch:
#   docker compose down -v && docker compose up -d
set -euo pipefail

DUMP=/dump/abcd_test.dump

echo "[01-restore] restoring ${DUMP} into database 'abcd'..."

# --no-owner/--no-privileges: every object in the dump is owned by `postgres`,
# which is already our superuser, so this is a no-op today. It keeps the
# restore working unchanged if POSTGRES_USER is ever renamed.
pg_restore \
  --username "${POSTGRES_USER}" \
  --dbname abcd \
  --no-owner \
  --no-privileges \
  --exit-on-error \
  --verbose \
  "${DUMP}"

echo "[01-restore] done."
