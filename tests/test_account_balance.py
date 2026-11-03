"""Testes do registro manual de saldo por conta.

O teste roda em uma transacao externa que sofre rollback no final, com engine
propria: o banco real nunca e alterado.
"""

import datetime
import decimal

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.infra.db.models import Account, AccountType, User
from app.infra.db.session import DATABASE_URL, get_db_session
from app.main import app

TEMP_ACCOUNT = "Teste-Saldo-Temporaria"
TODAY = datetime.date.today().isoformat()


@pytest.fixture
async def client():
    """Cliente HTTP com sessao isolada (savepoint + rollback) e conta temporaria."""
    local_engine = create_async_engine(DATABASE_URL)
    async with local_engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            user = (await session.execute(select(User).limit(1))).scalars().first()
            if user is None:
                user = User(name="Teste", email="teste@finscope.local")
                session.add(user)
                await session.flush()

            session.add(
                Account(
                    user_id=user.id,
                    name=TEMP_ACCOUNT,
                    type=AccountType.CHECKING,
                    initial_balance=decimal.Decimal("0.00"),
                    currency="BRL",
                    is_active=True,
                )
            )
            await session.flush()

            async def _get_session():
                yield session

            app.dependency_overrides[get_db_session] = _get_session
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
                yield http
        finally:
            app.dependency_overrides.clear()
            await session.close()
            await outer.rollback()
    await local_engine.dispose()


@pytest.mark.anyio
async def test_update_balance_registers_snapshot(client):
    response = await client.post(
        f"/api/accounts/{TEMP_ACCOUNT}/balance",
        json={"balance": 123.45, "date": TODAY},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["account"] == TEMP_ACCOUNT
    assert data["balance"] == 123.45
    assert data["date"] == TODAY
    assert data["total_balance"] > 0


@pytest.mark.anyio
async def test_dashboard_reflects_manual_balance(client):
    await client.post(
        f"/api/accounts/{TEMP_ACCOUNT}/balance",
        json={"balance": 987.65, "date": TODAY},
    )
    summary = (await client.get("/api/dashboard")).json()
    account = next(a for a in summary["accounts"] if a["name"] == TEMP_ACCOUNT)
    assert account["balance"] == 987.65
    assert account["balance_source"] == "snapshot"


@pytest.mark.anyio
async def test_same_date_overwrites_previous_balance(client):
    await client.post(
        f"/api/accounts/{TEMP_ACCOUNT}/balance",
        json={"balance": 10.0, "date": TODAY},
    )
    response = await client.post(
        f"/api/accounts/{TEMP_ACCOUNT}/balance",
        json={"balance": 25.5, "date": TODAY},
    )
    assert response.status_code == 200
    summary = (await client.get("/api/dashboard")).json()
    account = next(a for a in summary["accounts"] if a["name"] == TEMP_ACCOUNT)
    assert account["balance"] == 25.5


@pytest.mark.anyio
async def test_balance_defaults_to_today_when_date_omitted(client):
    response = await client.post(
        f"/api/accounts/{TEMP_ACCOUNT}/balance",
        json={"balance": 42.0},
    )
    assert response.status_code == 200
    assert response.json()["date"] == TODAY


@pytest.mark.anyio
async def test_unknown_account_returns_404(client):
    response = await client.post(
        "/api/accounts/Conta-Inexistente/balance",
        json={"balance": 10.0, "date": TODAY},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_invalid_date_returns_422(client):
    response = await client.post(
        f"/api/accounts/{TEMP_ACCOUNT}/balance",
        json={"balance": 10.0, "date": "21/10/2026"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_negative_balance_is_accepted(client):
    response = await client.post(
        f"/api/accounts/{TEMP_ACCOUNT}/balance",
        json={"balance": -15.5, "date": TODAY},
    )
    assert response.status_code == 200
    assert response.json()["balance"] == -15.5


@pytest.mark.anyio
async def test_spent_today_ignores_internal_transfers(client):
    """Transferência interna não entra no gasto do dia nem nos totais do mês."""
    future = "2099-01-01"
    for tx_type, category, amount, description in [
        ("Despesa", "Alimentação", 100.0, "Gasto real"),
        ("Despesa", "Transferência interna", 500.0, "Pix para conta própria"),
        ("Receita", "Salário", 300.0, "Receita real"),
        ("Receita", "Transferência interna", 700.0, "Pix recebido de conta própria"),
    ]:
        response = await client.post(
            "/api/transactions",
            json={
                "date": future,
                "type": tx_type,
                "category": category,
                "description": description,
                "amount": amount,
                "account": TEMP_ACCOUNT,
            },
        )
        assert response.status_code == 200

    summary = (await client.get(f"/api/dashboard?date={future}")).json()
    assert summary["spent_today"] == 100.0
    assert summary["expense_month"] == 100.0
    assert summary["income_month"] == 300.0
    assert summary["net_month"] == 200.0
