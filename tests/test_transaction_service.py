import uuid

import pytest
from sqlalchemy import select

from app.infra.db.models import Account
from app.infra.db.session import async_session_factory
from app.schemas import TransactionCreate
from app.services.transaction_service import TransactionService


@pytest.mark.anyio
async def test_statement_import_idempotency_uses_postgres() -> None:
    async with async_session_factory() as session:
        account = await session.scalar(select(Account).order_by(Account.name).limit(1))
        assert account is not None

        payload = TransactionCreate(
            date="2026-09-11",
            type="Despesa",
            category="Teste de importação",
            description="Teste de idempotência",
            amount=1,
            account=account.name,
        )
        service = TransactionService(session)
        external_id = f"test-import:{uuid.uuid4()}"

        created_transaction, created = await service.create(payload, external_id=external_id)
        repeated_transaction, repeated_created = await service.create(payload, external_id=external_id)

        assert created is True
        assert repeated_created is False
        assert repeated_transaction.id == created_transaction.id
        await session.rollback()
