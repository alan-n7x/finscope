# Finscope — Backlog de Issues & Roadmap de Migração

Este documento centraliza as issues e o roadmap para guiar o desenvolvimento do projeto no ambiente Linux nativo.

---

## 📌 Issue #1: Infraestrutura Docker (PostgreSQL 16 & Compose)
* **Labels:** `infrastructure`, `docker`
* **Status:** ✅ Concluído
* **Descrição:** Configurar a orquestração do ambiente com Docker para rodar o PostgreSQL de forma isolada e persistente.
* **Tarefas:**
  - [x] Criar `docker-compose.yml` com serviço `postgres:16-alpine`.
  - [x] Configurar volumes para persistência de dados (`finscope_pg_data`).
  - [x] Configurar healthcheck do PostgreSQL.
  - [x] Criar arquivo `.env.example` com variáveis de ambiente.
  - [x] Criar `Dockerfile.backend` otimizado com `uv`.

---

## 📌 Issue #2: Modelagem Relacional & Setup do Alembic (Async)
* **Labels:** `database`, `sqlalchemy`, `alembic`
* **Status:** ✅ Concluído
* **Descrição:** Estruturar a camada ORM com SQLAlchemy 2.0 assíncrono e versionamento de banco com Alembic.
* **Tarefas:**
  - [x] Configurar conexão assíncrona com `asyncpg` em `app/infra/db/session.py`.
  - [x] Criar modelos declarativos em `app/infra/db/models.py`:
    - `User`
    - `Account` (`AccountType`, `initial_balance`)
    - `Category` (`is_essential`, `parent_id`)
    - `Transaction` (`Numeric(14, 2)`, `TransactionType`, `TransactionStatus`, `external_id`)
    - `Transfer` (Partidas dobradas)
    - `Debt` (`DebtPriority`, `DebtStatus`, amortização)
    - `AccountBalanceSnapshot` (Fechamentos mensais)
  - [x] Configurar `migrations/env.py` apontando para `Base.metadata` e `DATABASE_URL`.

---

## 📌 Issue #3: Pipeline de ETL (Carga Inicial Excel ➔ PostgreSQL)
* **Labels:** `data-migration`, `etl`
* **Status:** ✅ Concluído
* **Descrição:** Script de carga única para migrar todo o histórico da planilha legada para o banco PostgreSQL com auditoria centavo a centavo.
* **Tarefas:**
  - [x] Criar script `scripts/migrate_excel_to_pg.py`.
  - [x] Leitura segura das abas `Lancamentos`, `Contas` e `Dividas` com `openpyxl`.
  - [x] Normalização e conversão de valores para `Decimal` e datas ISO.
  - [x] Execução atômica dentro de uma única transação no banco com rollback em caso de falha.
  - [x] Relatório de conferência pós-migração validando saldo cruzado.

---

## 📌 Issue #4: Desacoplamento da API FastAPI (Migração de Endpoints)
* **Labels:** `backend`, `fastapi`, `refactor`
* **Status:** ✅ Concluído
* **Descrição:** Substituir chamadas diretas a `excel_engine.py` por repositórios assíncronos do SQLAlchemy.
* **Tarefas:**
  - [x] Implementar `FinanceRepository` em `app/infra/repositories/finance_repository.py`.
  - [x] Conectar endpoints em `app/main.py` com injeção de dependência assíncrona (`get_db_session`).
  - [x] Implementar fallback gracioso caso o banco local esteja offline.

---

## 📌 Issue #5: Planilha como Relatório de Exportação (Output)
* **Labels:** `feature`, `reporting`, `excel`
* **Status:** ✅ Concluído
* **Descrição:** Transformar o Excel em um recurso de exportação/relatório gerado sob demanda.
* **Tarefas:**
  - [x] Criar serviço `ExcelExportService` em `app/services/excel_export_service.py`.
  - [x] Adicionar endpoint `GET /api/reports/export-excel` gerando `.xlsx` estilizado.

---

## 📌 Issue #6: Importação Multi-Banco Idempotente (Itaú PDF + Inter OFX)
* **Labels:** `feature`, `import`, `data-quality`
* **Status:** ✅ Concluído (PR #27)
* **Descrição:** Tornar o motor de importação multi-banco e seguro contra re-upload.
* **Tarefas:**
  - [x] Ids estáveis (FITID no OFX, hash no PDF) + `external_id` idempotente.
  - [x] Propagar `account_guess` por transação; snapshots na conta correta.
  - [x] Reconciliação exige mesma conta (evita falso match Itaú-out × Inter-in).
  - [x] Classificar transferências próprias sem inverter sinais do dashboard.
  - [x] Snapshot do `LEDGERBAL` no OFX; categoria `Estorno / Reembolso`.
  - [x] `tests/test_import_engine.py` com 7 testes.

---

## 📌 Issue #7: App Completo no Docker (API + Frontend em Imagem Única)
* **Labels:** `infrastructure`, `docker`, `frontend`
* **Status:** ✅ Concluído (PR #28)
* **Descrição:** Subir API + UI em um container na porta 8000 da LAN.
* **Tarefas:**
  - [x] `Dockerfile.backend` multi-stage (Node 22 builda o Vite; Python 3.14 roda tudo).
  - [x] `.dockerignore` (fora `.venv`, `node_modules`, `.git`, `.env`, `dist` local).
  - [x] Compose sem bind mount de dev, com `env_file` e healthcheck do backend.
  - [x] Corrigir `AppShell.tsx` (`Wallet` sem import, `BrandLogo` não usado — `tsc` falhava).

---

## 📌 Issue #9: Registro Manual de Saldo por Conta
* **Labels:** `feature`, `dashboard`, `data-quality`
* **Status:** ✅ Concluído
* **Descrição:** Permitir registrar o saldo bancário real de uma conta, para contas sem extrato importável (Mercado Livre/Pay, cartões).
* **Tarefas:**
  - [x] `POST /api/accounts/{nome}/balance` grava snapshot (upsert por conta+data).
  - [x] `FinanceRepository.update_account_balance` + 404 para conta inexistente/inativa.
  - [x] UI: botão "Atualizar saldo" no card da conta (dashboard) com modal de valor/data.
  - [x] `tests/test_account_balance.py` (7 testes, transação isolada com rollback).
  - [x] ETL: não descarta mais o "Saldo bancário atual" sem data — passa a avisar.

---

## 📌 Issue #8: Padronização de Documentação (Docstrings Google + Docs)
* **Labels:** `documentation`, `tech-debt`
* **Status:** ✅ Concluído (PR #29)
* **Descrição:** Docstrings Google em todo o código de produção e docs refletindo o estado atual.
* **Tarefas:**
  - [x] Docstrings `Args/Returns/Raises` em `app/` e `scripts/`.
  - [x] Reescrever `README.md` (stack, Docker, fluxo de importação, endpoints).
  - [x] Atualizar `docs/` (issues #6–#8, follow-ups).
  - [ ] Fora do escopo (convencional): `tests/` (padrão pytest), `scratch/` (descartável), `migrations/env.py` (boilerplate), `app/data/*.md` (referência legada).

---

## 📌 Issue #10: Edição de Lançamentos pelo Extrato
* **Labels:** `feature`, `api`, `frontend`
* **Status:** ✅ Concluído
* **Descrição:** Clicar em um lançamento do extrato para editar os mesmos campos do formulário de criação.
* **Tarefas:**
  - [x] `GET /api/transactions/{id}` (404 para id inválido/inexistente).
  - [x] `PATCH /api/transactions/{id}` com atualização parcial, `external_id` imutável e `409` para transferências vinculadas.
  - [x] Testes de consulta/edição e documentação do comportamento.
  - [x] UI: modal de edição reaproveitando o formulário.
  - [x] Invalidação de extrato, dashboard, cash-flow e analytics após salvar.

---

## 📌 Issue #11: Reconciliar Reimportação após Edição Manual
* **Labels:** `data-quality`, `import`, `tech-debt`
* **Status:** 📋 Backlog
* **Descrição:** O `external_id` da importação é um hash de `data|valor|tipo|descrição`. Editar um desses campos faz um re-upload do mesmo extrato enxergar o item como novo e potencialmente duplicá-lo.
* **Tarefas:**
  - [ ] Definir identidade estável independente dos campos editáveis (ex.: coluna `import_key`).
  - [ ] Ajustar `reconcile_transactions`/`confirm_import` para usar essa identidade.
  - [ ] Teste de reimportação após edição de valor/data/descrição.

---

## 🚀 Como Rodar no Linux:

1. Subir o banco PostgreSQL:
   ```bash
   docker compose up -d postgres
   ```
2. Executar a migração inicial e popular com a planilha:
   ```bash
   uv run python scripts/migrate_excel_to_pg.py
   ```
3. Rodar a aplicação:
   ```bash
   uv run uvicorn app.main:app --reload
   ```
