from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infra.db.models import (
    Account,
    Category,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.schemas import TransactionCreate, TransactionUpdate

_TRANSACTION_TYPES = {
    "receita": TransactionType.INCOME,
    "despesa": TransactionType.EXPENSE,
    "transferência": TransactionType.TRANSFER,
    "transferencia": TransactionType.TRANSFER,
}

_NON_NULLABLE_FIELDS = (
    "date",
    "type",
    "category",
    "description",
    "payment_method",
    "amount",
    "essential",
    "paid",
    "account",
)


class TransactionNotFoundError(Exception):
    """Lançamento inexistente para o id informado."""


class TransactionConflictError(Exception):
    """Lançamento não pode ser alterado no estado atual (ex.: transferência)."""


class TransactionService:
    """Cria e atualiza lançamentos; o PostgreSQL é a única fonte de verdade."""

    def __init__(self, session: AsyncSession) -> None:
        """Vincula o serviço a uma sessão assíncrona existente.

        Args:
            session: Sessão SQLAlchemy da operação atual.
        """
        self.session = session

    async def create(
        self,
        payload: TransactionCreate,
        *,
        external_id: str | None = None,
    ) -> tuple[Transaction, bool]:
        """Cria o lançamento resolvendo conta e categoria por nome (cria se faltar).

        Args:
            payload: Dados do lançamento (`TransactionCreate`).
            external_id: Chave de idempotência (ex.: `import:<id estável>`).
                Repetidos na mesma conta retornam o existente sem duplicar.

        Raises:
            ValueError: Data fora do formato YYYY-MM-DD, conta inexistente
                ou tipo diferente de Receita/Despesa/Transferência.

        Returns:
            Tupla (transação, True se criada / False se já existia).
        """
        transaction_date = self._parse_date(payload.date)
        account = await self._resolve_account(payload.account)

        if external_id:
            existing = await self.session.scalar(
                select(Transaction).where(
                    Transaction.account_id == account.id,
                    Transaction.external_id == external_id,
                )
            )
            if existing is not None:
                return existing, False

        category = await self._resolve_category(
            account, payload.category, essential=payload.essential
        )
        transaction_type = self._parse_type(payload.type)

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

    async def update(
        self,
        transaction_id: str,
        payload: TransactionUpdate,
    ) -> tuple[Transaction, bool]:
        """Atualiza parcialmente um lançamento existente.

        Apenas os campos enviados são alterados; `external_id` nunca muda para
        preservar a rastreabilidade da importação. Lançamentos ligados a uma
        transferência contábil (`transfer_id`) são bloqueados, pois editar uma
        ponta quebraria a partida dobrada.

        Args:
            transaction_id: UUID do lançamento em formato string.
            payload: Campos a alterar (`TransactionUpdate`).

        Raises:
            TransactionNotFoundError: Id inválido ou lançamento inexistente.
            TransactionConflictError: Lançamento vinculado a transferência.
            ValueError: Data/tipo/valor/conta inválidos ou campo obrigatório nulo.

        Returns:
            Tupla (transação, True se algo mudou / False se o payload era vazio).
        """
        try:
            tx_uuid = uuid.UUID(transaction_id)
        except (ValueError, AttributeError, TypeError) as exc:
            raise TransactionNotFoundError(
                f"Lançamento não encontrado: {transaction_id}"
            ) from exc

        transaction = await self.session.scalar(
            select(Transaction)
            .options(selectinload(Transaction.account), selectinload(Transaction.category))
            .where(Transaction.id == tx_uuid)
        )
        if transaction is None:
            raise TransactionNotFoundError(f"Lançamento não encontrado: {transaction_id}")

        if transaction.transfer_id is not None:
            raise TransactionConflictError(
                "Lançamento vinculado a uma transferência não pode ser editado."
            )

        data = payload.model_dump(exclude_unset=True)
        if not data:
            return transaction, False

        for field in _NON_NULLABLE_FIELDS:
            if field in data and data[field] is None:
                raise ValueError(f"O campo '{field}' não pode ser nulo.")

        account = transaction.account
        if "account" in data:
            account = await self._resolve_account(data["account"])
            transaction.account_id = account.id

        if "category" in data:
            category = await self._resolve_category(account, data["category"])
            transaction.category_id = category.id

        if "date" in data:
            transaction.date = self._parse_date(data["date"])
        if "type" in data:
            transaction.type = self._parse_type(data["type"])
        if "amount" in data:
            transaction.amount = Decimal(str(data["amount"]))
        if "description" in data:
            transaction.description = data["description"].strip() or "Sem descrição"
        if "payment_method" in data:
            transaction.payment_method = data["payment_method"].strip() or "Pix"
        if "essential" in data:
            transaction.is_essential = data["essential"]
        if "paid" in data:
            transaction.status = (
                TransactionStatus.POSTED if data["paid"] else TransactionStatus.PENDING
            )
        if "obs" in data:
            transaction.notes = data["obs"]

        await self.session.flush()
        return transaction, True

    @staticmethod
    def _parse_date(value: str) -> datetime.date:
        """Converte uma data ISO em `date`.

        Args:
            value: Data no formato YYYY-MM-DD.

        Raises:
            ValueError: Data fora do formato esperado.

        Returns:
            Data convertida.
        """
        try:
            return datetime.date.fromisoformat(value)
        except (ValueError, TypeError) as exc:
            raise ValueError("A data deve usar o formato YYYY-MM-DD.") from exc

    @staticmethod
    def _parse_type(value: str) -> TransactionType:
        """Converte o tipo em português para o enum do banco.

        Args:
            value: Receita, Despesa ou Transferência.

        Raises:
            ValueError: Tipo não reconhecido.

        Returns:
            Enum `TransactionType` correspondente.
        """
        transaction_type = _TRANSACTION_TYPES.get(str(value).strip().lower())
        if transaction_type is None:
            raise ValueError("Tipo deve ser Receita, Despesa ou Transferência.")
        return transaction_type

    async def _resolve_account(self, name: str) -> Account:
        """Busca a conta pelo nome (case-insensitive).

        Args:
            name: Nome da conta cadastrada.

        Raises:
            ValueError: Conta inexistente.

        Returns:
            Conta encontrada.
        """
        account = await self.session.scalar(
            select(Account).where(func.lower(Account.name) == name.strip().lower())
        )
        if account is None:
            raise ValueError(f"Conta não cadastrada: {name}")
        return account

    async def _resolve_category(
        self,
        account: Account,
        name: str,
        *,
        essential: bool = False,
    ) -> Category:
        """Busca a categoria do usuário ou cria uma nova com o nome informado.

        Args:
            account: Conta dona do lançamento (define o usuário).
            name: Nome da categoria (vazio cai em "Outros").
            essential: Marca a categoria como essencial ao criá-la.

        Returns:
            Categoria existente ou recém-criada.
        """
        category_name = (name or "").strip() or "Outros"
        category = await self.session.scalar(
            select(Category).where(
                Category.user_id == account.user_id,
                func.lower(Category.name) == category_name.lower(),
            )
        )
        if category is None:
            category = Category(
                user_id=account.user_id,
                name=category_name,
                is_essential=essential,
            )
            self.session.add(category)
            await self.session.flush()
        return category

    @staticmethod
    def serialize(transaction: Transaction) -> dict[str, Any]:
        """Converte a entidade para o formato de exibição da API/UI.

        Args:
            transaction: Lançamento com `account`/`category` carregados.

        Returns:
            Dicionário com datas ISO, tipo em português e valores float.
        """
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
