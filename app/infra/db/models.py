from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa com timestamps padrão de auditoria."""
    pass


# ============================================================================
# ENUMS DE DOMÍNIO
# ============================================================================

class TransactionType(str, enum.Enum):
    INCOME = "INCOME"       # Receita
    EXPENSE = "EXPENSE"     # Despesa
    TRANSFER = "TRANSFER"   # Movimentação interna entre contas


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"     # Previsto / Não pago
    POSTED = "POSTED"       # Liquidado / Confirmado
    CANCELED = "CANCELED"   # Cancelado


class AccountType(str, enum.Enum):
    CHECKING = "CHECKING"         # Conta Corrente
    CREDIT_CARD = "CREDIT_CARD"   # Cartão de Crédito
    INVESTMENT = "INVESTMENT"     # Investimentos / Tesouro
    CASH = "CASH"                 # Dinheiro Físico


class DebtPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DebtStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RENEGOTIATED = "RENEGOTIATED"
    PAID_OFF = "PAID_OFF"


# ============================================================================
# TABELAS DE DOMÍNIO
# ============================================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    accounts: Mapped[List[Account]] = relationship(back_populates="user", cascade="all, delete-orphan")
    categories: Mapped[List[Category]] = relationship(back_populates="user", cascade="all, delete-orphan")
    debts: Mapped[List[Debt]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="account_type_enum"), nullable=False, default=AccountType.CHECKING
    )
    initial_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="accounts")
    transactions: Mapped[List[Transaction]] = relationship(back_populates="account")
    snapshots: Mapped[List[AccountBalanceSnapshot]] = relationship(back_populates="account")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_account_user_name"),
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    is_essential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship(back_populates="categories")
    parent: Mapped[Optional[Category]] = relationship("Category", remote_side=[id])
    transactions: Mapped[List[Transaction]] = relationship(back_populates="category")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_category_user_name"),
    )


class Transfer(Base):
    """Representa a amarração contábil entre débito e crédito de uma transferência interna."""
    __tablename__ = "transfers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    destination_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    source_account: Mapped[Account] = relationship("Account", foreign_keys=[source_account_id])
    destination_account: Mapped[Account] = relationship("Account", foreign_keys=[destination_account_id])
    transactions: Mapped[List[Transaction]] = relationship(back_populates="transfer")

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_transfer_amount_positive"),
        CheckConstraint("source_account_id != destination_account_id", name="chk_distinct_accounts"),
    )


class Debt(Base):
    """Contratos de dívidas, financiamentos e acordos com amortização."""
    __tablename__ = "debts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    creditor: Mapped[str] = mapped_column(String(150), nullable=False)  # Ex: PGE-SP, Itaú
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    debt_type: Mapped[str] = mapped_column(String(100), nullable=False)  # Consignado, IPVA, etc.
    initial_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    installment_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total_installments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remaining_installments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    due_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    priority: Mapped[DebtPriority] = mapped_column(
        Enum(DebtPriority, name="debt_priority_enum"), nullable=False, default=DebtPriority.MEDIUM
    )
    status: Mapped[DebtStatus] = mapped_column(
        Enum(DebtStatus, name="debt_status_enum"), nullable=False, default=DebtStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="debts")
    amortizations: Mapped[List[Transaction]] = relationship(back_populates="debt")

    __table_args__ = (
        CheckConstraint("current_balance >= 0", name="chk_debt_balance_non_negative"),
        CheckConstraint("initial_amount >= 0", name="chk_debt_initial_positive"),
    )


class Transaction(Base):
    """Ledger transacional com integridade contábil e idempotência."""
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    debt_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    transfer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transfers.id", ondelete="CASCADE"), nullable=True, index=True
    )

    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type_enum"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False, default="Pix")
    is_essential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status_enum"), nullable=False, default=TransactionStatus.POSTED
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Identificador de Conciliação e Idempotência (FITID do OFX ou transactionId da Pluggy)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    account: Mapped[Account] = relationship(back_populates="transactions")
    category: Mapped[Optional[Category]] = relationship(back_populates="transactions")
    debt: Mapped[Optional[Debt]] = relationship(back_populates="amortizations")
    transfer: Mapped[Optional[Transfer]] = relationship(back_populates="transactions")

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_transaction_amount_positive"),
        UniqueConstraint("account_id", "external_id", name="uq_tx_account_external_id"),
        Index("ix_transactions_account_date", "account_id", "date"),
        Index("ix_transactions_date_type", "date", "type"),
    )


class AccountBalanceSnapshot(Base):
    """Fechamento contábil mensal de saldo para performance de queries analíticas."""
    __tablename__ = "account_balance_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)  # Último dia do mês
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    account: Mapped[Account] = relationship(back_populates="snapshots")

    __table_args__ = (
        UniqueConstraint("account_id", "snapshot_date", name="uq_account_snapshot_date"),
    )
