# Finscope — Controle Financeiro Pessoal

Controle financeiro de usuário único: dashboard com saldos por conta, extrato,
importação de extratos com conciliação, dívidas, fluxo de caixa realizado vs
projetado, exportação Excel e lançamento rápido via Telegram. Fonte única de
verdade: **PostgreSQL**.

## Funcionalidades

- **Dashboard**: saldo por conta ancorado no snapshot mais recente, receitas e
  despesas do mês, limite diário e saldo consolidado.
- **Extrato**: lançamentos com filtros de mês, categoria e status, além de busca
  textual.
- **Edição pelo extrato**: clique na linha (ou no ícone de lápis) para abrir o
  mesmo formulário de criação já preenchido; o salvamento usa `PATCH` e atualiza
  extrato, dashboard, fluxo de caixa e analytics sem recarregar a página.
- **Importação de extratos**: OFX (Inter, Santander, Nubank...) e PDF do Itaú,
  com preview, conciliação por conta e snapshots de saldo.
- **Dívidas**: parcelas e vencimentos em aberto.
- **Fluxo de caixa**: série diária de realizado vs. projetado.
- **Analytics**: distribuição de gastos por categoria e comparativo mensal.
- **Relatórios**: exportação `.xlsx` do mês.
- **Extras**: atualização manual de saldo de contas sem extrato importável e
  lançamento rápido via Telegram.

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
- **Analytics e limite diário**: receitas/despesas do mês, gasto do dia e
  pendências usadas no cálculo ignoram lançamentos na categoria
  `Transferência interna` (movimentação entre contas próprias não é consumo
  nem obrigação).
- **Snapshots**: `SALDO DO DIA` + "saldo em conta" do cabeçalho (Itaú) e
  `LEDGERBAL` (OFX); o dashboard ancora o saldo no snapshot mais recente.

### Edição de lançamentos

**Pela interface**: no extrato, clique na linha ou no ícone de lápis. O modal
"Editar Lançamento" carrega o detalhe atual (`GET /api/transactions/{id}`) e
mostra o mesmo formulário de criação já preenchido. Ao salvar, o `PATCH`
atualiza extrato, dashboard, fluxo de caixa e analytics sem recarregar a página.
O ícone de lápis é um `button` com `aria-label` (acessível por teclado) e a linha
funciona como atalho de mouse.

**Pela API**: `PATCH /api/transactions/{id}` altera apenas os campos enviados
(`amount`, `date`, `account`, `category`, etc.). O `external_id` da importação é
imutável e lançamentos ligados a uma transferência contábil (`transfer_id`)
retornam `409`.

Atenção ao editar um lançamento importado: o id estável é um hash de
`data|valor|tipo|descrição`. Se algum desses campos for alterado, um re-upload
do mesmo extrato pode enxergar o item como novo. Categoria, status, essencial e
observação não afetam o hash e são seguros de editar.

Detalhes de negócio e convenções do ledger em `app/data/*.md` (referência da
época da planilha) e `docs/`.

## Estado e cache no frontend

O estado de servidor fica no **React Query**; os componentes guardam apenas
estado de UI (filtros, modal aberto e rascunho do formulário).

- **Formulário único**: `TransactionForm` é compartilhado por
  `NewTransactionModal` e `EditTransactionModal`, então criação e edição têm os
  mesmos campos, validações e layout. O modal de edição usa `key={current.id}`
  para reinicializar o formulário se o lançamento em edição mudar.
- **Abertura instantânea + revalidação em background**: `useTransaction(id,
  initialData)` usa a linha que já está no extrato como `initialData` e marca
  `initialDataUpdatedAt: 0`. O modal abre imediatamente com os dados da tabela e
  o `GET /api/transactions/{id}` roda em background para confirmar o estado real.

Após salvar, `useUpdateTransaction` invalida as queries abaixo, e cada tela se
atualiza sozinha:

| Query key | Tela impactada |
| --------- | -------------- |
| `transactions` | Extrato e gráficos do Analytics |
| `transaction` | Detalhe do lançamento no modal |
| `dashboard` | Dashboard, Dívidas e resumo do Analytics |
| `cash-flow` | Fluxo de caixa |
| `filter-options` | Opções de filtros (categorias, contas, formas) |

Analytics não tem endpoint próprio: é derivado no cliente de `transactions` +
`dashboard`, portanto é atualizado pelas mesmas invalidações.

## Endpoints principais

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| GET | `/health` | Saúde do app + banco |
| GET | `/api/dashboard?month=&date=` | Saldos, mês e limite diário |
| GET | `/api/dashboard/cash-flow?month=&date=` | Série diária realizado/projetado |
| GET | `/api/transactions?...` | Extrato com filtros |
| GET | `/api/transactions/{id}` | Consulta um lançamento |
| POST | `/api/transactions` | Lançamento manual |
| PATCH | `/api/transactions/{id}` | Edição parcial de lançamento |
| GET | `/api/debts` | Dívidas |
| POST | `/api/accounts/{nome}/balance` | Registra o saldo real da conta |
| POST | `/api/transactions/import/upload` | Preview de extrato |
| POST | `/api/transactions/import/confirm` | Confirma importação |
| GET | `/api/reports/export-excel?month=` | Relatório `.xlsx` |
| GET | `/api/options` | Opções dos filtros da UI |

No frontend, `GET /api/transactions/{id}` e `PATCH /api/transactions/{id}`
formam o par usado pelo modal de edição do extrato: o `GET` preenche o
formulário e o `PATCH` envia apenas os campos alterados.

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
