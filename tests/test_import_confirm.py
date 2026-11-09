"""Testes da confirmação de importação com categoria editada no preview.

O teste roda em transação externa com rollback: o banco real não é alterado.
"""

import decimal

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.infra.db.models import (
    Account,
    AccountType,
    Category,
    Transaction,
    User,
)
from app.infra.db.session import DATABASE_URL, get_db_session
from app.main import app

TEMP_ACCOUNT = "Teste-Import-Categoria"
EXTERNAL_ID = "import:teste-categoria-editada"


@pytest.fixture
async def import_client():
    """Cliente HTTP com conta temporária e sessão isolada."""
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
                yield http, session
        finally:
            app.dependency_overrides.clear()
            await session.close()
            await outer.rollback()
    await local_engine.dispose()


@pytest.mark.anyio
async def test_confirm_import_persiste_categoria_editada(import_client):
    http, session = import_client

    response = await http.post(
        "/api/transactions/import/confirm",
        json={
            "transactions": [
                {
                    "id": "teste-categoria-editada",
                    "date": "2099-01-15",
                    "type": "Despesa",
                    "description": "Compra com categoria ajustada",
                    "amount": 42.50,
                    "status": "NEW",
                    "category": "Transporte",
                    "account": TEMP_ACCOUNT,
                }
            ]
        },
    )

    assert response.status_code == 200, response.text
    assert "1 itens adicionados" in response.json()["message"]

    category_name = await session.scalar(
        select(Category.name)
        .join(Transaction, Transaction.category_id == Category.id)
        .where(Transaction.external_id == EXTERNAL_ID)
    )
    assert category_name == "Transporte"
