# Finscope — guia para agentes

## Fonte de verdade

- O PostgreSQL é a fonte oficial do ledger.
- Leitura financeira passa por `app/infra/repositories/finance_repository.py`.
- Escrita passa por `app/services/transaction_service.py`.
- Novas agregações de negócio devem virar método de repositório + teste.

## SQL e enums (regra obrigatória)

Enums do domínio (`TransactionType`, `TransactionStatus`) **nunca** devem ser
interpolados em SQL como texto. Use o ORM ou parâmetros vinculados:

```python
# certo — ORM
Transaction.type == TransactionType.INCOME

# certo — SQL puro com bind
text("... WHEN t.type = :tipo ...").bindparams(tipo=TransactionType.INCOME)

# errado — interpolação/escape manual; pode virar '''INCOME'''
text(f"... WHEN t.type = '{tipo}' ...")
```

Sintomas dessa classe de erro:

```text
invalid input value for enum transaction_type_enum: "'INCOME'"
```

Consultas ad-hoc devem usar o wrapper do container, com heredoc para evitar
escaping de aspas:

```bash
./scripts/psql.sh <<'SQL'
SELECT count(*) FROM transactions;
SQL
```

Evite `python -c` com SQL multilinha dentro de aspas do shell: o escape de
aspas é a origem mais comum de literais como `'''INCOME'''`.

## Validação antes de PR

```bash
uv run pytest
cd frontend && npm run lint && npm run build
```

## Ambiente de desenvolvimento

- `./scripts/dev.sh`: backend em Docker com bind mount + `--reload` e Vite/HMR.
- `docker compose up -d --build backend`: artefato de produção local.
- Detalhes em `README.md`.
