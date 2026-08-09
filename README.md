# Pluggy MVP — Meu Extrato Bancário

MVP local, de usuário único, para conectar uma conta bancária pelo Pluggy Connect e consultar contas e transações. O backend mantém somente o último `itemId` em SQLite; credenciais e tokens bancários não são armazenados.

## Pré-requisitos

- Python 3.14
- [`uv`](https://docs.astral.sh/uv/)
- Uma aplicação criada no Dashboard da Pluggy, com `clientId` e `clientSecret`

## Configuração

Copie o arquivo de exemplo e edite `.env`:

```bash
cp .env.example .env
```

No PowerShell, use `Copy-Item .env.example .env`. Preencha somente no `.env`:

```env
PLUGGY_CLIENT_ID=seu-client-id
PLUGGY_CLIENT_SECRET=seu-client-secret
PLUGGY_API_URL=https://api.pluggy.ai
DATABASE_URL=sqlite+aiosqlite:///./pluggy.db
```

O `.env` está no `.gitignore`. Nunca versione esse arquivo, credenciais reais, API keys ou Connect Tokens.

## Instalar, testar e executar

```bash
uv sync
uv run pytest
uv run uvicorn app.main:app --reload
```

Abra `http://localhost:8000`. A documentação interativa fica em `http://localhost:8000/docs`.

Clique em **Conectar banco**, escolha a instituição no widget da Pluggy e conclua a autorização. Depois da sincronização, selecione uma conta e o período do extrato.

## Limitações e segurança

Este projeto é deliberadamente um MVP local: há apenas um usuário, o último `itemId` substitui o anterior, o polling ocorre no navegador e cada consulta retorna no máximo 500 transações. Não há login, webhook nem mecanismo de revogação. Alguns fluxos longos de autorização podem terminar depois que a página for fechada e, sem webhook, o MVP não receberá esse evento.

Antes de publicar na internet, implemente autenticação e autorização, HTTPS, gestão segura de segredos, proteção contra abuso, auditoria, política de privacidade/LGPD, webhooks validados e controles de acesso aos dados financeiros.

## Contratos Pluggy utilizados

- `POST /auth` para uma API key temporária (mantida apenas em memória)
- `POST /connect_token` com `options.clientUserId`
- `GET /items/{id}` e `GET /accounts?itemId=...`
- `GET /v2/transactions` com `dateFrom`, `dateTo` e cursor `after`
- Pluggy Connect para JavaScript puro `v2.8.2`, conforme o quickstart oficial consultado em julho de 2026
