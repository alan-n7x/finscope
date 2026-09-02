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
