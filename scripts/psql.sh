#!/usr/bin/env bash
# Executa SQL no Postgres do Compose sem sofrimento de escaping.
#
# Uso:
#   ./scripts/psql.sh -c "SELECT 1"
#   ./scripts/psql.sh <<'SQL'
#   SELECT count(*) FROM transactions;
#   SQL
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

exec docker compose exec -T postgres psql \
  -v ON_ERROR_STOP=1 \
  -U "${POSTGRES_USER:-postgres}" \
  -d "${POSTGRES_DB:-finscope}" \
  "$@"
