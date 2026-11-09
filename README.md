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
- **Importação de extratos**: OFX (Inter, Santander, Nubank...), PDF do Itaú e
  PDF do Mercado Pago, com preview, conciliação por conta e snapshots de saldo.
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
- **Importação:** OFX genérico (`ofxparse`) e PDF do Itaú/Mercado Pago (`pdfplumber`)
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

O `docker-compose.yml` é o artefato de produção: imagem imutável, sem bind
mount e sem reload. Para desenvolver, use o override `compose.dev.yaml`, que
monta `./app` no container e roda o Uvicorn com `--reload`.

```bash
# backend em Docker (reload) + frontend com Vite/HMR
./scripts/dev.sh

# ou manualmente:
docker compose -f docker-compose.yml -f compose.dev.yaml up -d postgres backend
cd frontend && npm install && npm run dev
```

- Backend: `http://localhost:8000` (salvar um `.py` reinicia o Uvicorn).
- Frontend: `http://localhost:5173` (HMR; proxy `/api` → `:8000`).
- Docs: `http://localhost:8000/docs`.

Se preferir o backend fora do Docker, o banco continua no container:

```bash
docker compose up -d postgres
uv sync
uv run pytest
uv run uvicorn app.main:app --reload   # http://localhost:8000
```

## Como funciona a importação de extratos

`POST /api/transactions/import/upload` aceita `.ofx` (Inter, Santander,
Nubank...), `.pdf` do Itaú ou `.pdf` do Mercado Pago e devolve preview com
status `NEW`/`MATCHED`, palpite de conta e snapshots de saldo.
`POST /api/transactions/import/confirm` grava só os `NEW` (idempotente) e
atualiza os saldos da conta correta.

Regras de negócio em `app/import_rules.py` e `app/categorization.py`; leitura
de cada formato em `app/parsers/` (um módulo por banco).

- **Ids estáveis**: FITID no OFX, hash `itau|data|valor|tipo|descrição` no PDF
  do Itaú e id da operação no PDF do Mercado Pago — re-upload gera os mesmos
  `external_id` (`import:<id>`) e não duplica.
- **Conciliação por conta**: valor + tipo iguais com tolerância de 2 dias, e
  mesma conta quando ambos os lados a informam (evita falso match entre as
  pernas de uma transferência Itaú ↔ Inter).
- **Transferências próprias** (`ALAN DO...`): saída → `Despesa`, entrada com
  "recebido" → `Transferência`, entrada Itaú sem "recebido" → `Receita`, sempre
  com categoria `Transferência interna` (preserva os sinais do dashboard).
- **Categorização conservadora**: descrições com marcas conhecidas viram
  `Alimentação`, `Transporte`, `Telefone`, `Assinaturas`, `Carro`, `Dívidas` ou
  `Salário`; o resto continua em `Outros`. Regras em `app/categorization.py` e
  backfill de lançamentos antigos em `scripts/recategorize_transactions.py`
  ([guia](docs/CATEGORIZATION.md)).
- **Categoria revisável no preview**: o upload sugere a categoria e o modal de
  importação permite trocá-la nos itens `NEW` antes de confirmar. Itens
  `MATCHED`/`IGNORED` não são gravados, então o seletor fica desabilitado.
- **Analytics e limite diário**: receitas/despesas do mês, gasto do dia e
  pendências usadas no cálculo ignoram lançamentos na categoria
  `Transferência interna` (movimentação entre contas próprias não é consumo
  nem obrigação). O gráfico por categoria usa `GET /api/analytics/summary`,
  que aplica a mesma regra no backend.
- **Snapshots**: `SALDO DO DIA` + "saldo em conta" do cabeçalho (Itaú),
  `LEDGERBAL` (OFX) e `Saldo final` do período (Mercado Pago); o dashboard
  ancora o saldo no snapshot mais recente.
- **Layouts de PDF**: cada banco tem um módulo em `app/parsers/`
  (`ofx.py`, `itau.py`, `mercadopago.py`) com detecção e extração próprias; o
  Mercado Pago ainda valida contra os totais impressos no extrato — se o
  layout mudar, o upload falha com `422` e uma mensagem acionável em vez de
  importar errado. Passo a passo em [`docs/PARSERS.md`](docs/PARSERS.md).

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
| `transactions` | Extrato |
| `transaction` | Detalhe do lançamento no modal |
| `dashboard` | Dashboard, Dívidas e comparativo mensal do Analytics |
| `analytics` | Distribuição de gastos por categoria no Analytics |
| `cash-flow` | Fluxo de caixa |
| `filter-options` | Opções de filtros (categorias, contas, formas) |

O gráfico de categorias do Analytics consome `GET /api/analytics/summary`, que
agrega no backend as despesas confirmadas do mês e ignora `Transferência
interna`. Assim o gráfico não depende do limite de 200 itens de
`GET /api/transactions` e usa a mesma regra do dashboard.

## Endpoints principais

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| GET | `/health` | Saúde do app + banco |
| GET | `/api/dashboard?month=&date=` | Saldos, mês e limite diário |
| GET | `/api/dashboard/cash-flow?month=&date=` | Série diária realizado/projetado |
| GET | `/api/analytics/summary?month=` | Despesas confirmadas por categoria |
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
