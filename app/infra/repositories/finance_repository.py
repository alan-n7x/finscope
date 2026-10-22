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
from app.services.daily_limit import compute_daily_limit
from app.services.cash_balance import compute_cash_balance


class FinanceRepository:
    """Consultas agregadas do ledger; única porta de leitura financeira da API."""

    def __init__(self, session: AsyncSession) -> None:
        """Vincula o repositório a uma sessão assíncrona existente.

        Args:
            session: Sessão SQLAlchemy da requisição atual.
        """
        self.session = session

    async def update_account_balance(
        self,
        account_name: str,
        balance: Decimal,
        snapshot_date: datetime.date,
    ) -> dict[str, Any]:
        """Registra o saldo bancário real da conta como snapshot (upsert).

        O snapshot ancora o saldo do dashboard: a partir dele, o repositório
        soma apenas os lançamentos posteriores. É o equivalente ao "Saldo
        bancário atual" da planilha e serve para contas sem extrato
        importável (ex.: Mercado Livre/Pay).

        Args:
            account_name: Nome da conta (ex.: "Mercado Pago").
            balance: Saldo real informado pelo usuário.
            snapshot_date: Data do saldo (YYYY-MM-DD).

        Raises:
            ValueError: Quando a conta não existe ou está inativa.

        Returns:
            Dicionário com conta, saldo registrado e data do snapshot.
        """
        acc_stmt = select(Account).where(
            Account.name == account_name,
            Account.is_active.is_(True),
        )
        acc_res = await self.session.execute(acc_stmt)
        account = acc_res.scalar_one_or_none()
        if account is None:
            raise ValueError(f"Conta não encontrada ou inativa: {account_name}")

        snap_stmt = select(AccountBalanceSnapshot).where(
            AccountBalanceSnapshot.account_id == account.id,
            AccountBalanceSnapshot.snapshot_date == snapshot_date,
        )
        snap_res = await self.session.execute(snap_stmt)
        snapshot = snap_res.scalar_one_or_none()

        if snapshot is None:
            snapshot = AccountBalanceSnapshot(
                account_id=account.id,
                snapshot_date=snapshot_date,
                balance=balance,
            )
            self.session.add(snapshot)
        else:
            snapshot.balance = balance

        await self.session.commit()
        return {
            "account": account.name,
            "balance": float(balance),
            "date": snapshot_date.isoformat(),
        }

    async def get_dashboard_summary(self, month: Optional[str] = None, date: Optional[str] = None) -> dict[str, Any]:
        """Calcula o resumo do dashboard na data de referência.

        Saldo por conta prefere o snapshot bancário mais recente + ledger
        posterior; receitas/despesas consideram POSTED até a data de referência.

        Args:
            month: Mês alvo no formato YYYY-MM (usa o último dia ou hoje).
            date: Data de referência no formato YYYY-MM-DD (precede `month`).

        Returns:
            Dicionário com saldos, agregados do mês, limite diário e contas.
        """
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

        # 3. Limite diario recomendado (compromissos pendentes do mes alvo)
        pending_stmt = select(
            func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))
        ).where(
            Transaction.type == TransactionType.EXPENSE,
            Transaction.status == TransactionStatus.PENDING,
            Transaction.date >= start_date,
            Transaction.date < end_date,
        )
        pending_res = await self.session.execute(pending_stmt)
        pending_month = pending_res.scalar_one()

        spent_day_stmt = select(
            func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))
        ).where(
            Transaction.type == TransactionType.EXPENSE,
            Transaction.status == TransactionStatus.POSTED,
            Transaction.date == ref_date,
        )
        spent_day_res = await self.session.execute(spent_day_stmt)
        spent_ref_day = spent_day_res.scalar_one()

        daily_limit = compute_daily_limit(
            total_balance=float(total_balance),
            pending_month=float(pending_month),
            spent_ref_day=float(spent_ref_day),
            ref_date=ref_date,
            target_month=target_month,
        )

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
            **daily_limit,
        }

    async def get_filter_options(self) -> dict[str, Any]:
        """Lista valores distintos para os filtros da UI (categorias, contas, meses...).

        Returns:
            Dicionário com categorias, formas de pagamento, contas, meses e tipos.
        """
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
        """Lista lançamentos com filtros opcionais, mais recentes primeiro.

        Args:
            month: Filtra pelo mês no formato YYYY-MM.
            category: Substring da categoria (case-insensitive).
            search: Substring da descrição ou observações.
            status: "Sim" (POSTED) ou "Não"/"Nao" (PENDING).
            limit: Máximo de itens (o endpoint limita a 500).

        Returns:
            Lançamentos serializados para exibição, com conta e categoria resolvidas.
        """
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
        """Lista dívidas ordenadas pelo maior saldo devedor.

        Returns:
            Dívidas serializadas com prioridade em português e vencimento.
        """
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

    async def get_cash_flow(
        self, month: Optional[str] = None, date: Optional[str] = None
    ) -> dict[str, Any]:
        """Agrega lancamentos por dia do mes alvo com saldo realizado/projetado.

        Mantem os campos historicos (entradas/saidas confirmadas por dia e
        acumulados) e adiciona a serie de saldos: realized usa apenas
        POSTED ate o dia de transicao; projected parte desse ponto e
        incorpora PENDING pela data do lancamento. Transferencias nao
        entram na serie.

        Args:
            month: Mês alvo no formato YYYY-MM.
            date: Data de referência no formato YYYY-MM-DD (define o mês alvo).

        Returns:
            Dicionário com dias, data de transição, saldo inicial, projeção
            final e flag de projeção existente.
        """
        today = datetime.date.today()
        if date:
            try:
                ref = datetime.date.fromisoformat(date)
            except ValueError:
                ref = today
            target_month = ref.strftime("%Y-%m")
        elif month:
            try:
                datetime.date(int(month.split("-")[0]), int(month.split("-")[1]), 1)
                target_month = month
            except (ValueError, IndexError, AttributeError):
                target_month = today.strftime("%Y-%m")
        else:
            target_month = today.strftime("%Y-%m")

        year, mon = int(target_month.split("-")[0]), int(target_month.split("-")[1])
        start_date = datetime.date(year, mon, 1)
        if mon == 12:
            end_date = datetime.date(year + 1, 1, 1)
        else:
            end_date = datetime.date(year, mon + 1, 1)
        last_day = (end_date - datetime.timedelta(days=1)).day

        async def _net_by_day(status: TransactionStatus) -> dict[int, float]:
            """Soma o líquido (receitas − despesas) por dia do mês para um status.

            Args:
                status: POSTED (realizado) ou PENDING (projetado).

            Returns:
                Mapa dia do mês -> líquido em reais (transferências excluídas).
            """
            stmt = (
                select(
                    Transaction.date,
                    func.coalesce(func.sum(
                        case(
                            (Transaction.type == TransactionType.INCOME, Transaction.amount),
                            else_=-Transaction.amount,
                        )
                    ), Decimal("0.00")),
                )
                .where(
                    Transaction.status == status,
                    Transaction.type.in_([TransactionType.INCOME, TransactionType.EXPENSE]),
                    Transaction.date >= start_date,
                    Transaction.date < end_date,
                )
                .group_by(Transaction.date)
            )
            res = await self.session.execute(stmt)
            return {tx_date.day: float(total) for tx_date, total in res.all()}

        stmt = (
            select(
                Transaction.date,
                Transaction.type,
                func.coalesce(func.sum(Transaction.amount), Decimal("0.00")),
            )
            .where(
                Transaction.status == TransactionStatus.POSTED,
                Transaction.type.in_([TransactionType.INCOME, TransactionType.EXPENSE]),
                Transaction.date >= start_date,
                Transaction.date < end_date,
            )
            .group_by(Transaction.date, Transaction.type)
        )
        res = await self.session.execute(stmt)

        per_day: dict[str, dict[str, float]] = {}
        for tx_date, tx_type, total in res.all():
            key = tx_date.isoformat()
            bucket = per_day.setdefault(key, {"income": 0.0, "expense": 0.0})
            bucket["income" if tx_type == TransactionType.INCOME else "expense"] = float(total)

        # Ancora: saldo total na data de transicao (reutiliza o calculo
        # oficial do dashboard via snapshots + ledger, sem duplicar logica).
        # Mes futuro nao tem dia confirmado: ancora no saldo de hoje e toda
        # a serie vira projecao.
        summary = await self.get_dashboard_summary(month=month, date=date)
        anchor_total = float(summary["total_balance"])
        posted_net = await _net_by_day(TransactionStatus.POSTED)
        pending_net = await _net_by_day(TransactionStatus.PENDING)
        transition_date: str | None
        if target_month > today.strftime("%Y-%m"):
            transition_day = 0
            transition_date = None
            start_balance = round(anchor_total, 2)
        else:
            transition_day = min(today.day, last_day) if target_month == today.strftime("%Y-%m") else last_day
            transition_date = datetime.date(year, mon, transition_day).isoformat()
            posted_to_transition = round(sum(
                net for day, net in posted_net.items() if day <= transition_day
            ), 2)
            start_balance = round(anchor_total - posted_to_transition, 2)

        balance_series = compute_cash_balance(
            start_balance=start_balance,
            posted_net_by_day=posted_net,
            pending_net_by_day=pending_net,
            year=year,
            month=mon,
            transition_day=transition_day,
        )
        balance_by_day = {item["day"]: item for item in balance_series}
        has_projection = any(
            day > transition_day and net != 0.0 for day, net in pending_net.items()
        )

        days = []
        acc_income = 0.0
        acc_expense = 0.0
        for day in range(1, last_day + 1):
            d = datetime.date(year, mon, day)
            bucket = per_day.get(d.isoformat(), {"income": 0.0, "expense": 0.0})
            acc_income = round(acc_income + bucket["income"], 2)
            acc_expense = round(acc_expense + bucket["expense"], 2)
            balance = balance_by_day[day]
            days.append({
                "day": day,
                "date": d.isoformat(),
                "income": round(bucket["income"], 2),
                "expense": round(bucket["expense"], 2),
                "cumulative_income": acc_income,
                "cumulative_expense": acc_expense,
                "net": round(acc_income - acc_expense, 2),
                "realized_balance": balance["realized_balance"],
                "projected_balance": balance["projected_balance"],
            })

        return {
            "month": target_month,
            "days": days,
            "transition_date": transition_date,
            "start_balance": start_balance,
            "final_projected_balance": balance_series[-1]["projected_balance"],
            "has_projection": has_projection,
        }
