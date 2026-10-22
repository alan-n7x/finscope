# Finscope — Controle Financeiro Pessoal

Controle financeiro de usuário único: dashboard com saldos por conta, extrato,
importação de extratos com conciliação, dívidas, fluxo de caixa realizado vs
projetado, exportação Excel e lançamento rápido via Telegram. Fonte única de
verdade: **PostgreSQL**.

## Stack

- **Backend:** FastAPI + SQLAlchemy 2.0 assíncrono (`asyncpg`), Pydantic v2
- **Banco:** PostgreSQL 16 (Docker, volume persistente)
- **Frontend:** React 19 + Vite + React Query, servido pelo próprio backend em `:8000`
- **Importação:** OFX genérico (`ofxparse`) e PDF do Itaú (`pdfplumber`)
- **Extras:** bot do Telegram (`aiogram`), exportação `.xlsx` (`openpyxl`)

## Pré-requisitos

- Docker + Docker Compose (banco e app)
- Python 3.14 + [`uv`](https://docs.astral.sh/uv/) (desenvolvimento local do backend)
- Node 22 + npm (desenvolvimento do frontend; o build Docker é autocontido)

## Configuração

```bash
cp .env.example .env
```

Ajuste no `.env` (nunca versione este arquivo): credenciais do Postgres,
`DATABASE_URL`, `PLUGGY_*` (opcional, Open Finance) e `TELEGRAM_*` (opcional).
O container do backend recebe o `.env` via `env_file` e sobrescreve a
`DATABASE_URL` para o host `postgres` do Compose.

## Rodando tudo no Docker (recomendado)

```bash
docker compose up -d --build
```

- App completo (API + UI): `http://<ip-da-maquina>:8000`
- Saúde: `GET /health` (aguarda o Postgres via `depends_on` + healthchecks)
- O volume `finscope_pg_data` preserva os dados entre rebuilds.

## Desenvolvimento local

```bash
# banco
docker compose up -d postgres

# backend
uv sync
uv run pytest
uv run uvicorn app.main:app --reload   # http://localhost:8000

# frontend (outro terminal)
cd frontend && npm install && npm run dev  # http://localhost:5173 (proxy /api -> :8000)
```

Documentação interativa: `http://localhost:8000/docs`.

## Como funciona a importação de extratos

`POST /api/transactions/import/upload` aceita `.ofx` (Inter, Santander,
Nubank...) ou `.pdf` do Itaú e devolve preview com status `NEW`/`MATCHED`,
palpite de conta e snapshots de saldo. `POST /api/transactions/import/confirm`
grava só os `NEW` (idempotente) e atualiza os saldos da conta correta.

Regras em `app/import_engine.py`:

- **Ids estáveis**: FITID no OFX, hash `itau|data|valor|tipo|descrição` no PDF —
  re-upload gera os mesmos `external_id` (`import:<id>`) e não duplica.
- **Conciliação por conta**: valor + tipo iguais com tolerância de 2 dias, e
  mesma conta quando ambos os lados a informam (evita falso match entre as
  pernas de uma transferência Itaú ↔ Inter).
- **Transferências próprias** (`ALAN DO...`): saída → `Despesa`, entrada com
  "recebido" → `Transferência`, entrada Itaú sem "recebido" → `Receita`, sempre
  com categoria `Transferência interna` (preserva os sinais do dashboard).
- **Snapshots**: `SALDO DO DIA` + "saldo em conta" do cabeçalho (Itaú) e
  `LEDGERBAL` (OFX); o dashboard ancora o saldo no snapshot mais recente.

Detalhes de negócio e convenções do ledger em `app/data/*.md` (referência da
época da planilha) e `docs/`.

## Endpoints principais

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| GET | `/health` | Saúde do app + banco |
| GET | `/api/dashboard?month=&date=` | Saldos, mês e limite diário |
| GET | `/api/dashboard/cash-flow?month=&date=` | Série diária realizado/projetado |
| GET | `/api/transactions?...` | Extrato com filtros |
| POST | `/api/transactions` | Lançamento manual |
| GET | `/api/debts` | Dívidas |
| POST | `/api/accounts/{nome}/balance` | Registra o saldo real da conta |
| POST | `/api/transactions/import/upload` | Preview de extrato |
| POST | `/api/transactions/import/confirm` | Confirma importação |
| GET | `/api/reports/export-excel?month=` | Relatório `.xlsx` |
| GET | `/api/options` | Opções dos filtros da UI |

## Atualizar o saldo de uma conta

Contas **sem extrato importável** (Mercado Livre/Pay, cartões, contas de
parceiros) não recebem importação de OFX/PDF, então o app não tem como saber
o saldo delas sozinho. Nesses casos, use **"Atualizar saldo"** no card da
conta (dashboard) ou chame a API:

```bash
curl -X POST "http://localhost:8000/api/accounts/Mercado%20Pago/balance" \
  -H "Content-Type: application/json" \
  -d '{"balance": 250.75, "date": "2026-10-21"}'
```

O valor vira um *snapshot* na data informada e passa a ancorar o dashboard:
lançamentos **posteriores** a essa data continuam somando normalmente, e
repetir na mesma data sobrescreve o valor. É o equivalente ao "Saldo bancário
atual" da planilha original.

## Convenções de código

- Docstrings no padrão **Google** (`Args`/`Returns`/`Raises`) em todo o código
  de produção (`app/`, `scripts/`). `tests/` segue convenção pytest,
  `scratch/` é descartável e `migrations/env.py` é boilerplate do Alembic.
- Commits atômicos por branch de feature (`feat/`, `fix/`, `chore/`, `docs/`)
  com PR para `main` contendo o quê, validação e o que ficou de fora.

## Limitações e segurança

MVP local de usuário único: sem autenticação, CORS aberto e sem revogação de
sessões. Projetado para LAN confiável — antes de expor na internet, implementar
auth, HTTPS, gestão de segredos, rate limiting, auditoria e webhooks validados
(ver `docs/ideias_futuras.md`).
