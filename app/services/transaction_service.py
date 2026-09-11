from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models import (
    Account,
    Category,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.schemas import TransactionCreate


class TransactionService:
    """Creates ledger entries without allowing another store to become authoritative."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        payload: TransactionCreate,
        *,
        external_id: str | None = None,
    ) -> tuple[Transaction, bool]:
        try:
            transaction_date = datetime.date.fromisoformat(payload.date)
        except ValueError as exc:
            raise ValueError("A data deve usar o formato YYYY-MM-DD.") from exc

        account = await self.session.scalar(
            select(Account).where(func.lower(Account.name) == payload.account.strip().lower())
        )
        if account is None:
            raise ValueError(f"Conta não cadastrada: {payload.account}")

        if external_id:
            existing = await self.session.scalar(
                select(Transaction).where(
                    Transaction.account_id == account.id,
                    Transaction.external_id == external_id,
                )
            )
            if existing is not None:
                return existing, False

        category = await self.session.scalar(
            select(Category).where(
                Category.user_id == account.user_id,
                func.lower(Category.name) == payload.category.strip().lower(),
            )
        )
        if category is None:
            category = Category(
                user_id=account.user_id,
                name=payload.category.strip(),
                is_essential=payload.essential,
            )
            self.session.add(category)
            await self.session.flush()

        type_map = {
            "receita": TransactionType.INCOME,
            "despesa": TransactionType.EXPENSE,
            "transferência": TransactionType.TRANSFER,
            "transferencia": TransactionType.TRANSFER,
        }
        transaction_type = type_map.get(payload.type.strip().lower())
        if transaction_type is None:
            raise ValueError("Tipo deve ser Receita, Despesa ou Transferência.")

        transaction = Transaction(
            account_id=account.id,
            category_id=category.id,
            date=transaction_date,
            amount=Decimal(str(payload.amount)),
            type=transaction_type,
            description=payload.description.strip() or "Sem descrição",
            payment_method=payload.payment_method.strip() or "Pix",
            is_essential=payload.essential,
            status=TransactionStatus.POSTED if payload.paid else TransactionStatus.PENDING,
            notes=payload.obs,
            external_id=external_id,
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction, True

    @staticmethod
    def serialize(transaction: Transaction) -> dict[str, Any]:
        type_display = {
            TransactionType.INCOME: "Receita",
            TransactionType.EXPENSE: "Despesa",
            TransactionType.TRANSFER: "Transferência",
        }[transaction.type]
        return {
            "id": str(transaction.id),
            "date": transaction.date.isoformat(),
            "month": transaction.date.strftime("%Y-%m"),
            "type": type_display,
            "category": transaction.category.name if transaction.category else "Outros",
            "description": transaction.description,
            "payment_method": transaction.payment_method,
            "amount": float(transaction.amount),
            "essential": "Sim" if transaction.is_essential else "Não",
            "paid": "Sim" if transaction.status == TransactionStatus.POSTED else "Não",
            "obs": transaction.notes or "",
            "account": transaction.account.name if transaction.account else "",
        }
