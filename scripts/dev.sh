#!/usr/bin/env bash
# Sobe o backend em modo dev (bind mount + --reload) e o frontend com Vite/HMR.
#
# Uso: ./scripts/dev.sh
# Ao encerrar com Ctrl+C, o container do backend é parado; o Postgres continua.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Caminhos absolutos: o trap roda depois do `cd frontend`.
COMPOSE=(docker compose -f "$ROOT_DIR/docker-compose.yml" -f "$ROOT_DIR/compose.dev.yaml")

cleanup() {
  "${COMPOSE[@]}" stop backend >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

# Usa a imagem já construída; o Compose só builda se ela não existir.
"${COMPOSE[@]}" up -d postgres backend

# Espera o backend responder antes de abrir o Vite.
backend_ready=false
for _ in $(seq 1 60); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    backend_ready=true
    break
  fi
  sleep 1
done

if [ "$backend_ready" != true ]; then
  echo "Backend não respondeu em 60s; veja os logs:" >&2
  echo "  ${COMPOSE[*]} logs backend" >&2
  exit 1
fi

echo "Backend (reload): http://localhost:8000"
echo "Frontend (HMR):   http://localhost:5173"

cd frontend
if [ ! -d node_modules ]; then
  npm ci
fi
npm run dev
