"""Testes do resumo de Analytics por categoria no backend.

Os testes de agregação rodam em uma transação externa com rollback no final,
usando um mês futuro isolado para não depender dos dados reais.
"""

import datetime
import decimal

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.infra.db.models import (
    Account,
    AccountType,
    Category,
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
)
from app.infra.db.session import DATABASE_URL, get_db_session
from app.main import app

MONTH = "2099-01"
OTHER_MONTH = "2099-02"
TEMP_ACCOUNT = "Teste-Analytics-Temporaria"
CATEGORY_A = "Teste-Analytics-A"
INTERNAL_CATEGORY = "Transferência interna"


def _tx(
    account_id,
    tx_date: datetime.date,
    amount: str,
    *,
    category_id=None,
    tx_type: TransactionType = TransactionType.EXPENSE,
    status: TransactionStatus = TransactionStatus.POSTED,
) -> Transaction:
    """Cria um lançamento de teste com os campos obrigatórios."""
    return Transaction(
        account_id=account_id,
        category_id=category_id,
        date=tx_date,
        amount=decimal.Decimal(amount),
        type=tx_type,
        description="Lançamento de teste",
        payment_method="Pix",
        status=status,
    )


async def _get_or_create_category(session, user_id, name: str) -> Category:
    """Reaproveita categorias já existentes (ex.: ``Transferência interna``)."""
    category = await session.scalar(
        select(Category).where(Category.user_id == user_id, Category.name == name)
    )
    if category is None:
        category = Category(user_id=user_id, name=name)
        session.add(category)
        await session.flush()
    return category


@pytest.fixture
async def analytics_client():
    """Cliente HTTP com dados isolados para o mês ``2099-01``."""
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

            account = Account(
                user_id=user.id,
                name=TEMP_ACCOUNT,
                type=AccountType.CHECKING,
                initial_balance=decimal.Decimal("0.00"),
                currency="BRL",
                is_active=True,
            )
            session.add(account)
            await session.flush()

            category_a = await _get_or_create_category(session, user.id, CATEGORY_A)
            internal = await _get_or_create_category(session, user.id, INTERNAL_CATEGORY)

            session.add_all(
                [
                    # Despesas confirmadas no mês alvo, categoria A: 150.
                    _tx(account.id, datetime.date(2099, 1, 5), "100.00", category_id=category_a.id),
                    _tx(account.id, datetime.date(2099, 1, 6), "50.00", category_id=category_a.id),
                    # Sem categoria -> Outros: 30.
                    _tx(account.id, datetime.date(2099, 1, 7), "30.00"),
                    # Não entram: pendente, transferência interna, receita e outro mês.
                    _tx(
                        account.id,
                        datetime.date(2099, 1, 8),
                        "25.00",
                        category_id=category_a.id,
                        status=TransactionStatus.PENDING,
                    ),
                    _tx(
                        account.id,
                        datetime.date(2099, 1, 9),
                        "999.00",
                        category_id=internal.id,
                    ),
                    _tx(
                        account.id,
                        datetime.date(2099, 1, 10),
                        "500.00",
                        category_id=category_a.id,
                        tx_type=TransactionType.INCOME,
                    ),
                    _tx(
                        account.id,
                        datetime.date(2099, 2, 1),
                        "200.00",
                        category_id=category_a.id,
                    ),
                ]
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
async def test_resumo_agrega_despesas_posted_e_exclui_transferencia_interna(analytics_client):
    response = await analytics_client.get(f"/api/analytics/summary?month={MONTH}")

    assert response.status_code == 200
    data = response.json()
    assert data["month"] == MONTH
    assert data["total_expenses"] == 180.0
    assert data["categories"] == [
        {"name": CATEGORY_A, "value": 150.0, "percentage": 83.3},
        {"name": "Outros", "value": 30.0, "percentage": 16.7},
    ]


@pytest.mark.anyio
async def test_resumo_rejeita_mes_invalido(analytics_client):
    response = await analytics_client.get("/api/analytics/summary?month=2026-13")

    assert response.status_code == 422
    assert "YYYY-MM" in response.json()["detail"]


@pytest.mark.anyio
async def test_resumo_sem_despesas_retorna_lista_vazia(analytics_client):
    response = await analytics_client.get("/api/analytics/summary?month=2099-03")

    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2099-03"
    assert data["total_expenses"] == 0
    assert data["categories"] == []


def test_resumo_bate_com_a_despesa_do_dashboard():
    with TestClient(app) as client:
        analytics = client.get("/api/analytics/summary?month=2026-09").json()
        dashboard = client.get("/api/dashboard?month=2026-09").json()

    assert analytics["total_expenses"] == pytest.approx(
        dashboard["expense_month"], abs=0.01
    )
