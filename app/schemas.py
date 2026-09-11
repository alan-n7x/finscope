from typing import Any
from pydantic import BaseModel, Field


class AccountSummary(BaseModel):
    name: str
    type: str
    balance: float
    balance_source: str = "ledger"


class DashboardSummaryResponse(BaseModel):
    month: str
    ref_date: str | None = None
    total_balance: float
    income_month: float
    expense_month: float
    net_month: float
    projected_final: float
    reserve_min: float
    free_after_reserve: float
    accounts: list[AccountSummary]


class TransactionItem(BaseModel):
    id: str
    date: str
    month: str
    type: str
    category: str
    description: str
    payment_method: str
    amount: float
    essential: str
    paid: str
    obs: str | None = None
    account: str


class TransactionCreate(BaseModel):
    date: str = Field(description="Data no formato YYYY-MM-DD")
    type: str = Field(default="Despesa", description="Despesa, Receita ou Transferência")
    category: str = Field(default="Outros")
    description: str = Field(default="")
    payment_method: str = Field(default="Pix")
    amount: float = Field(gt=0, description="Valor da transação")
    essential: bool = Field(default=False)
    paid: bool = Field(default=True)
    obs: str | None = None
    account: str = Field(default="Itaú - Conta corrente")


class DebtItem(BaseModel):
    creditor: str
    type: str
    balance: float
    installment: float
    due_date: str
    priority: str
    status: str


class FilterOptionsResponse(BaseModel):
    categories: list[str]
    payment_methods: list[str]
    accounts: list[str]
    months: list[str]
    types: list[str]


class ImportTransaction(BaseModel):
    id: str
    date: str
    type: str
    description: str
    amount: float
    status: str
    category: str | None = None
    account: str | None = None
    similarity_score: float | None = None

class ImportPreviewResponse(BaseModel):
    transactions: list[ImportTransaction]
    account_guess: str | None = None

class ImportConfirmRequest(BaseModel):
    transactions: list[ImportTransaction]
