from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, List, Optional
import uuid

from sqlalchemy import select, func, desc, or_, case, and_, not_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infra.db.models import (
    Account,
    AccountBalanceSnapshot,
    Category,
    Debt,
    DebtPriority,
    DebtStatus,
    Transaction,
    TransactionType,
    TransactionStatus,
)


class FinanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_dashboard_summary(self, month: Optional[str] = None, date: Optional[str] = None) -> dict[str, Any]:
        # Resolve a data de referencia: usa 'date' se fornecido, senao extrai do 'month', senao hoje
        today = datetime.date.today()
        if date:
            try:
                ref_date = datetime.date.fromisoformat(date)
            except ValueError:
                ref_date = today
        elif month:
            try:
                year_m, month_m = month.split("-")
                y, m = int(year_m), int(month_m)
                # Ultimo dia do mes solicitado; se for o mes corrente usa hoje
                if m == 12:
                    last_day_of_month = datetime.date(y, 12, 31)
                else:
                    last_day_of_month = datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)
                ref_date = min(last_day_of_month, today)
            except (ValueError, AttributeError):
                ref_date = today
        else:
            ref_date = today

        target_month = ref_date.strftime("%Y-%m")

        # 1. Contas e Saldos Calculados via Ledger
        acc_stmt = select(Account).where(Account.is_active == True).order_by(Account.name)
        acc_res = await self.session.execute(acc_stmt)
        accounts = acc_res.scalars().all()

        accounts_list = []
        total_balance = Decimal("0.00")

        for acc in accounts:
            # Preferencia 1: snapshot mais recente (saldo bancario real confirmado)
            snap_stmt = (
                select(AccountBalanceSnapshot)
                .where(
                    AccountBalanceSnapshot.account_id == acc.id,
                    AccountBalanceSnapshot.snapshot_date <= ref_date,
                )
                .order_by(desc(AccountBalanceSnapshot.snapshot_date))
                .limit(1)
            )
            snap_res = await self.session.execute(snap_stmt)
            latest_snapshot = snap_res.scalar_one_or_none()

            if latest_snapshot is not None:
                # Usa o saldo real do banco + lancamentos POSTERIORES ao snapshot e ATE ref_date
                post_snap_stmt = select(
                    func.coalesce(
                        func.sum(
                            case(
                                (Transaction.type == TransactionType.INCOME, Transaction.amount),
                                (Transaction.type == TransactionType.EXPENSE, -Transaction.amount),
                                (and_(Transaction.type == TransactionType.TRANSFER, Transaction.description.ilike("%recebido%")), Transaction.amount),
                                (and_(Transaction.type == TransactionType.TRANSFER, not_(Transaction.description.ilike("%recebido%"))), -Transaction.amount),
                                else_=Decimal("0.00"),
                            )
                        ),
                        Decimal("0.00"),
                    )
                ).where(
                    Transaction.account_id == acc.id,
                    Transaction.status == TransactionStatus.POSTED,
                    Transaction.date > latest_snapshot.snapshot_date,
                    Transaction.date <= ref_date,
                )
                post_snap_res = await self.session.execute(post_snap_stmt)
                acc_balance = latest_snapshot.balance + post_snap_res.scalar_one()
                balance_source = "snapshot"
            else:
                # Fallback: initial_balance + lancamentos POSTED ate ref_date
                bal_stmt = select(
                    func.coalesce(
                        func.sum(
                            case(
                                (Transaction.type == TransactionType.INCOME, Transaction.amount),
                                (Transaction.type == TransactionType.EXPENSE, -Transaction.amount),
                                (and_(Transaction.type == TransactionType.TRANSFER, Transaction.description.ilike("%recebido%")), Transaction.amount),
                                (and_(Transaction.type == TransactionType.TRANSFER, not_(Transaction.description.ilike("%recebido%"))), -Transaction.amount),
                                else_=Decimal("0.00"),
                            )
                        ),
                        Decimal("0.00"),
                    )
                ).where(
                    Transaction.account_id == acc.id,
                    Transaction.status == TransactionStatus.POSTED,
                    Transaction.date <= ref_date,
                )
                bal_res = await self.session.execute(bal_stmt)
                acc_balance = bal_res.scalar_one() + acc.initial_balance
                balance_source = "ledger"

            accounts_list.append({
                "name": acc.name,
                "type": acc.type.value if hasattr(acc.type, "value") else str(acc.type),
                "balance": float(acc_balance),
                "balance_source": balance_source,
            })
            total_balance += acc_balance

        # 2. Receitas e Despesas do mes da data de referencia
        year_str, month_str = target_month.split("-")
        start_date = datetime.date(int(year_str), int(month_str), 1)
        if int(month_str) == 12:
            end_date = datetime.date(int(year_str) + 1, 1, 1)
        else:
            end_date = datetime.date(int(year_str), int(month_str) + 1, 1)
        # Receitas/despesas consideram apenas ate a data de referencia dentro do mes
        cutoff_date = min(ref_date, end_date - datetime.timedelta(days=1))

        income_stmt = select(
            func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))
        ).where(
            Transaction.type == TransactionType.INCOME,
            Transaction.status == TransactionStatus.POSTED,
            Transaction.date >= start_date,
            Transaction.date <= cutoff_date,
        )
        income_res = await self.session.execute(income_stmt)
        income_month = income_res.scalar_one()

        expense_stmt = select(
            func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))
        ).where(
            Transaction.type == TransactionType.EXPENSE,
            Transaction.status == TransactionStatus.POSTED,
            Transaction.date >= start_date,
            Transaction.date <= cutoff_date,
        )
        expense_res = await self.session.execute(expense_stmt)
        expense_month = expense_res.scalar_one()

        reserve_min = Decimal("310.00")
        projected_final = total_balance + income_month - expense_month
        free_after_reserve = projected_final - reserve_min

        return {
            "month": target_month,
            "ref_date": ref_date.isoformat(),
            "total_balance": round(float(total_balance), 2),
            "income_month": round(float(income_month), 2),
            "expense_month": round(float(expense_month), 2),
            "net_month": round(float(income_month - expense_month), 2),
            "projected_final": round(float(projected_final), 2),
            "reserve_min": round(float(reserve_min), 2),
            "free_after_reserve": round(float(free_after_reserve), 2),
            "accounts": accounts_list,
        }

    async def get_filter_options(self) -> dict[str, Any]:
        cat_stmt = select(Category.name).order_by(Category.name)
        cat_res = await self.session.execute(cat_stmt)
        categories = cat_res.scalars().all()

        acc_stmt = select(Account.name).order_by(Account.name)
        acc_res = await self.session.execute(acc_stmt)
        accounts = acc_res.scalars().all()

        pay_stmt = select(Transaction.payment_method).distinct()
        pay_res = await self.session.execute(pay_stmt)
        payment_methods = [p for p in pay_res.scalars().all() if p]

        # Extrai meses únicos existentes nas transações
        months_stmt = select(
            func.to_char(Transaction.date, "YYYY-MM").label("month_str")
        ).distinct().order_by(desc("month_str"))
        months_res = await self.session.execute(months_stmt)
        months = months_res.scalars().all()

        return {
            "categories": sorted(list(categories)),
            "payment_methods": sorted(list(set(payment_methods))),
            "accounts": sorted(list(accounts)),
            "months": list(months) if months else [datetime.date.today().strftime("%Y-%m")],
            "types": ["Despesa", "Receita", "Transferência"],
        }

    async def list_transactions(
        self,
        month: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
    ) -> List[dict[str, Any]]:
        stmt = (
            select(Transaction)
            .options(selectinload(Transaction.account), selectinload(Transaction.category))
            .order_by(desc(Transaction.date), desc(Transaction.created_at))
        )

        if month:
            year_str, month_str = month.split("-")
            start_date = datetime.date(int(year_str), int(month_str), 1)
            if int(month_str) == 12:
                end_date = datetime.date(int(year_str) + 1, 1, 1)
            else:
                end_date = datetime.date(int(year_str), int(month_str) + 1, 1)
            stmt = stmt.where(Transaction.date >= start_date, Transaction.date < end_date)

        if category:
            stmt = stmt.join(Transaction.category).where(Category.name.ilike(f"%{category}%"))

        if status:
            if status.lower() == "sim":
                stmt = stmt.where(Transaction.status == TransactionStatus.POSTED)
            elif status.lower() == "não" or status.lower() == "nao":
                stmt = stmt.where(Transaction.status == TransactionStatus.PENDING)

        if search:
            q = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Transaction.description.ilike(q),
                    Transaction.notes.ilike(q),
                )
            )

        stmt = stmt.limit(limit)
        res = await self.session.execute(stmt)
        txs = res.scalars().all()

        results = []
        for t in txs:
            type_display = "Despesa"
            if t.type == TransactionType.INCOME:
                type_display = "Receita"
            elif t.type == TransactionType.TRANSFER:
                type_display = "Transferência"

            paid_display = "Sim" if t.status == TransactionStatus.POSTED else "Não"

            results.append({
                "id": str(t.id),
                "date": t.date.strftime("%Y-%m-%d"),
                "month": t.date.strftime("%Y-%m"),
                "type": type_display,
                "category": t.category.name if t.category else "Outros",
                "description": t.description,
                "payment_method": t.payment_method,
                "amount": float(t.amount),
                "essential": "Sim" if t.is_essential else "Não",
                "paid": paid_display,
                "obs": t.notes or "",
                "account": t.account.name if t.account else "Itaú - Conta corrente",
            })

        return results

    async def list_debts(self) -> List[dict[str, Any]]:
        stmt = select(Debt).order_by(desc(Debt.current_balance))
        res = await self.session.execute(stmt)
        debts = res.scalars().all()

        results = []
        for d in debts:
            priority_str = "Média"
            if d.priority == DebtPriority.HIGH:
                priority_str = "Alta"
            elif d.priority == DebtPriority.CRITICAL:
                priority_str = "Crítica"
            elif d.priority == DebtPriority.LOW:
                priority_str = "Baixa"

            results.append({
                "creditor": d.creditor,
                "type": d.debt_type,
                "balance": float(d.current_balance),
                "installment": float(d.installment_amount),
                "due_date": f"Dia {d.due_day}" if d.due_day else "",
                "priority": priority_str,
                "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            })
        return results
