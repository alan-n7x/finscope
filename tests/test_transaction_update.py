"""Testes da consulta e edição de lançamentos via API.

Cada teste roda em uma transacao externa com rollback no final, usando contas
temporarias: o banco real nunca e alterado.
"""

import datetime
import decimal
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.infra.db.models import (
    Account,
    AccountType,
    Transaction,
    TransactionStatus,
    TransactionType,
    Transfer,
    User,
)
from app.infra.db.session import DATABASE_URL, get_db_session
from app.main import app
from app.schemas import TransactionCreate
from app.services.transaction_service import TransactionService

ORIGIN_ACCOUNT = "Teste-Edicao-Origem"
DESTINATION_ACCOUNT = "Teste-Edicao-Destino"
EDIT_DATE = "2099-06-10"
EDIT_MONTH = "2099-06"


@pytest.fixture
async def context():
    """Cliente HTTP + sessao isolada (savepoint + rollback) e contas temporarias."""
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

            origin = Account(
                user_id=user.id,
                name=ORIGIN_ACCOUNT,
                type=AccountType.CHECKING,
                initial_balance=decimal.Decimal("0.00"),
                currency="BRL",
                is_active=True,
            )
            destination = Account(
                user_id=user.id,
                name=DESTINATION_ACCOUNT,
                type=AccountType.CHECKING,
                initial_balance=decimal.Decimal("0.00"),
                currency="BRL",
                is_active=True,
            )
            session.add_all([origin, destination])
            await session.flush()

            async def _get_session():
                yield session

            app.dependency_overrides[get_db_session] = _get_session
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
                yield SimpleNamespace(
                    http=http,
                    session=session,
                    user_id=user.id,
                    origin_id=origin.id,
                    destination_id=destination.id,
                )
        finally:
            app.dependency_overrides.clear()
            await session.close()
            await outer.rollback()
    await local_engine.dispose()


async def _create_transaction(context, **overrides):
    """Cria um lançamento via API e devolve o payload retornado."""
    payload = {
        "date": EDIT_DATE,
        "type": "Despesa",
        "category": "Outros",
        "description": "Lançamento de teste",
        "payment_method": "Pix",
        "amount": 100.0,
        "essential": False,
        "paid": True,
        "account": ORIGIN_ACCOUNT,
    }
    payload.update(overrides)
    response = await context.http.post("/api/transactions", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.anyio
async def test_get_transaction_by_id(context):
    created = await _create_transaction(context, description="Consulta por id")

    response = await context.http.get(f"/api/transactions/{created['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert data["description"] == "Consulta por id"
    assert data["account"] == ORIGIN_ACCOUNT
    assert data["category"] == "Outros"


@pytest.mark.anyio
async def test_get_transaction_not_found(context):
    missing = await context.http.get("/api/transactions/00000000-0000-0000-0000-000000000000")
    malformed = await context.http.get("/api/transactions/nao-e-um-uuid")

    assert missing.status_code == 404
    assert malformed.status_code == 404


@pytest.mark.anyio
async def test_patch_transaction_updates_only_sent_fields(context):
    created = await _create_transaction(context)

    response = await context.http.patch(
        f"/api/transactions/{created['id']}",
        json={"amount": 250.0, "category": "Alimentação", "obs": "Editado"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 250.0
    assert data["category"] == "Alimentação"
    assert data["obs"] == "Editado"
    # Campos nao enviados permanecem como estavam.
    assert data["date"] == EDIT_DATE
    assert data["description"] == created["description"]
    assert data["account"] == ORIGIN_ACCOUNT


@pytest.mark.anyio
async def test_patch_transaction_empty_payload_is_noop(context):
    created = await _create_transaction(context)

    response = await context.http.patch(f"/api/transactions/{created['id']}", json={})

    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.anyio
async def test_patch_transaction_can_change_account_and_status(context):
    created = await _create_transaction(context)

    response = await context.http.patch(
        f"/api/transactions/{created['id']}",
        json={"account": DESTINATION_ACCOUNT, "paid": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["account"] == DESTINATION_ACCOUNT
    assert data["paid"] == "Não"


@pytest.mark.anyio
async def test_patch_transaction_not_found(context):
    response = await context.http.patch(
        "/api/transactions/00000000-0000-0000-0000-000000000000",
        json={"amount": 10.0},
    )
    malformed = await context.http.patch(
        "/api/transactions/nao-e-um-uuid",
        json={"amount": 10.0},
    )

    assert response.status_code == 404
    assert malformed.status_code == 404


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        {"date": "10/06/2099"},
        {"type": "Investimento"},
        {"amount": 0},
        {"amount": -5},
        {"amount": None},
        {"account": "Conta inexistente"},
        {"description": None},
    ],
)
async def test_patch_transaction_invalid_payload(context, payload):
    created = await _create_transaction(context)

    response = await context.http.patch(f"/api/transactions/{created['id']}", json=payload)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_patch_preserves_import_external_id(context):
    service = TransactionService(context.session)
    transaction, created = await service.create(
        TransactionCreate(
            date=EDIT_DATE,
            type="Despesa",
            category="Outros",
            description="Importado",
            amount=10.0,
            account=ORIGIN_ACCOUNT,
        ),
        external_id="test:update:preserve",
    )
    assert created is True
    await context.session.commit()
    transaction_id = transaction.id

    response = await context.http.patch(
        f"/api/transactions/{transaction_id}",
        json={"amount": 99.0},
    )

    assert response.status_code == 200
    await context.session.refresh(transaction)
    assert transaction.external_id == "test:update:preserve"
    assert transaction.amount == decimal.Decimal("99.00")


@pytest.mark.anyio
async def test_patch_linked_transfer_returns_conflict(context):
    transfer = Transfer(
        user_id=context.user_id,
        source_account_id=context.origin_id,
        destination_account_id=context.destination_id,
        amount=decimal.Decimal("50.00"),
        date=datetime.date(2099, 6, 1),
    )
    context.session.add(transfer)
    await context.session.flush()

    transaction = Transaction(
        account_id=context.origin_id,
        date=datetime.date(2099, 6, 1),
        amount=decimal.Decimal("50.00"),
        type=TransactionType.TRANSFER,
        description="Transferência vinculada",
        payment_method="Pix",
        is_essential=False,
        status=TransactionStatus.POSTED,
        transfer_id=transfer.id,
    )
    context.session.add(transaction)
    await context.session.flush()
    await context.session.commit()
    transaction_id = transaction.id

    response = await context.http.patch(
        f"/api/transactions/{transaction_id}",
        json={"amount": 10.0},
    )

    assert response.status_code == 409


@pytest.mark.anyio
async def test_patch_reflects_in_dashboard(context):
    before = (
        await context.http.get(f"/api/dashboard?month={EDIT_MONTH}&date={EDIT_DATE}")
    ).json()

    created = await _create_transaction(context, amount=100.0)
    response = await context.http.patch(
        f"/api/transactions/{created['id']}",
        json={"amount": 250.0},
    )
    assert response.status_code == 200

    after = (
        await context.http.get(f"/api/dashboard?month={EDIT_MONTH}&date={EDIT_DATE}")
    ).json()
    origin = next(a for a in after["accounts"] if a["name"] == ORIGIN_ACCOUNT)

    assert round(after["expense_month"] - before["expense_month"], 2) == 250.0
    assert origin["balance"] == -250.0
