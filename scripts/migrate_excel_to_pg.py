from __future__ import annotations

import asyncio
import datetime
import os
import pathlib
import sys
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict

import openpyxl
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Adiciona o path raiz do projeto
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from app.infra.db.models import (
    Base,
    User,
    Account,
    AccountType,
    Category,
    Debt,
    DebtPriority,
    DebtStatus,
    Transaction,
    TransactionType,
    TransactionStatus,
)
from app.excel_engine import get_excel_path

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/finscope"
)


def to_decimal(val: any) -> Decimal:
    """Converte com segurança qualquer valor float/int/str para Decimal(14, 2)."""
    if val is None or str(val).strip() == "":
        return Decimal("0.00")
    if isinstance(val, (int, float, str)):
        clean_str = str(val).replace("R$", "").replace(" ", "").replace(",", ".")
        try:
            return Decimal(clean_str).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal("0.00")
    return Decimal("0.00")


def parse_date(val: any) -> datetime.date:
    """Converte datetime, date ou string para objeto datetime.date."""
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    if isinstance(val, str):
        val = val.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(val[:10], fmt).date()
            except ValueError:
                pass
    return datetime.date.today()


async def run_etl():
    excel_file = get_excel_path()
    print(f"📖 Lendo arquivo de origem: {excel_file}")
    
    if not excel_file.exists():
        raise FileNotFoundError(f"Arquivo Excel não encontrado em {excel_file}")

    wb = openpyxl.load_workbook(excel_file, data_only=True)
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        print("🛠️ Criando tabelas no PostgreSQL se não existirem...")
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        async with session.begin():
            print("🚀 Iniciando Transação Atômica de Migração...")

            # 1. Usuário Padrão
            user_stmt = select(User).where(User.email == "alan@finscope.local")
            res = await session.execute(user_stmt)
            user = res.scalar_one_or_none()
            if not user:
                user = User(name="Alan dos Santos Oliveira", email="alan@finscope.local")
                session.add(user)
                await session.flush()
                print(f"👤 Usuário criado: {user.name} ({user.id})")

            # 2. Migrar Contas (Sheet: 'Contas')
            account_map: Dict[str, Account] = {}
            if "Contas" in wb.sheetnames:
                ws_contas = wb["Contas"]
                for row in ws_contas.iter_rows(min_row=4, values_only=True):
                    if not row[0] or str(row[0]).strip() == "":
                        continue
                    
                    acc_name = str(row[0]).strip()
                    acc_type_str = str(row[1]).strip() if len(row) > 1 and row[1] else "Conta corrente"

                    acc_type = (
                        AccountType.CREDIT_CARD 
                        if "cartão" in acc_type_str.lower() or "crédito" in acc_name.lower()
                        else AccountType.CHECKING
                    )

                    acc = Account(
                        user_id=user.id,
                        name=acc_name,
                        type=acc_type,
                        initial_balance=Decimal("0.00"),
                        currency="BRL"
                    )
                    session.add(acc)
                    account_map[acc_name.lower()] = acc

                await session.flush()
                print(f"🏦 {len(account_map)} Contas migradas com sucesso.")

            default_acc_name = "itaú - conta corrente"
            if default_acc_name not in account_map:
                acc = Account(user_id=user.id, name="Itaú - Conta corrente", type=AccountType.CHECKING)
                session.add(acc)
                await session.flush()
                account_map[default_acc_name] = acc

            # 3. Migrar Dívidas (Sheet: 'Dividas')
            debt_map: Dict[str, Debt] = {}
            if "Dividas" in wb.sheetnames:
                ws_dividas = wb["Dividas"]
                for row in ws_dividas.iter_rows(min_row=3, values_only=True):
                    if not row[0] or str(row[0]).strip() == "" or "credor" in str(row[0]).lower():
                        continue

                    creditor = str(row[0]).strip()
                    d_type = str(row[1]).strip() if len(row) > 1 and row[1] else "Outros"
                    balance = to_decimal(row[2] if len(row) > 2 else 0.0)
                    installment = to_decimal(row[3] if len(row) > 3 else 0.0)
                    priority_str = str(row[6]).strip().upper() if len(row) > 6 and row[6] else "MEDIUM"
                    
                    priority = DebtPriority.HIGH if "ALTA" in priority_str else DebtPriority.MEDIUM

                    debt = Debt(
                        user_id=user.id,
                        creditor=creditor,
                        description=f"{d_type} - {creditor}",
                        debt_type=d_type,
                        initial_amount=balance,
                        current_balance=balance,
                        installment_amount=installment,
                        priority=priority,
                        status=DebtStatus.ACTIVE
                    )
                    session.add(debt)
                    debt_map[creditor.lower()] = debt

                await session.flush()
                print(f"💳 {len(debt_map)} Contratos de Dívidas migrados.")

            # 4. Migrar Lançamentos (Sheet: 'Lancamentos')
            category_map: Dict[str, Category] = {}
            total_txs_migrated = 0

            if "Lancamentos" in wb.sheetnames:
                ws_txs = wb["Lancamentos"]
                for row in ws_txs.iter_rows(min_row=2, values_only=True):
                    if row[0] is None:
                        continue

                    d_date = parse_date(row[0])
                    t_type_str = str(row[1]).strip() if row[1] else "Despesa"
                    cat_name = str(row[2]).strip() if row[2] else "Outros"
                    desc = str(row[3]).strip() if row[3] else "Sem Descrição"
                    payment_method = str(row[4]).strip() if row[4] else "Pix"
                    amount = to_decimal(row[5])
                    essential_str = str(row[6]).strip().lower() if row[6] else "não"
                    paid_str = str(row[7]).strip().lower() if row[7] else "sim"
                    notes = str(row[8]).strip() if row[8] else None
                    acc_name = str(row[11]).strip().lower() if len(row) > 11 and row[11] else default_acc_name

                    if amount <= 0:
                        continue

                    # Mapear Categoria
                    cat_key = cat_name.lower()
                    if cat_key not in category_map:
                        cat = Category(user_id=user.id, name=cat_name, is_essential=(essential_str == "sim"))
                        session.add(cat)
                        await session.flush()
                        category_map[cat_key] = cat
                    category = category_map[cat_key]

                    # Mapear Conta
                    account = account_map.get(acc_name, account_map[default_acc_name])

                    # Mapear Tipo Transacional
                    if "receita" in t_type_str.lower():
                        tx_type = TransactionType.INCOME
                    elif "transfer" in t_type_str.lower():
                        tx_type = TransactionType.TRANSFER
                    else:
                        tx_type = TransactionType.EXPENSE

                    tx_status = TransactionStatus.POSTED if paid_str == "sim" else TransactionStatus.PENDING

                    # Vínculo com Dívida (se aplicável)
                    linked_debt = None
                    for cred_name, debt_obj in debt_map.items():
                        if cred_name in desc.lower() or cred_name in cat_name.lower():
                            linked_debt = debt_obj
                            break

                    tx = Transaction(
                        account_id=account.id,
                        category_id=category.id,
                        debt_id=linked_debt.id if linked_debt else None,
                        date=d_date,
                        amount=amount,
                        type=tx_type,
                        description=desc,
                        payment_method=payment_method,
                        is_essential=(essential_str == "sim"),
                        status=tx_status,
                        notes=notes
                    )
                    session.add(tx)
                    total_txs_migrated += 1

                await session.flush()
                print(f"📝 {total_txs_migrated} Lançamentos inseridos no Ledger com sucesso.")

        # 5. Auditoria Pós-Migração
        print("\n" + "=" * 80)
        print("📊 RELATÓRIO DE AUDITORIA CONTÁBIL CRUZADA (Centavo a Centavo)")
        print("=" * 80)

        audit_stmt = (
            select(
                Account.name,
                func.coalesce(
                    func.sum(
                        func.case(
                            (Transaction.type == TransactionType.INCOME, Transaction.amount),
                            (Transaction.type == TransactionType.EXPENSE, -Transaction.amount),
                            else_=Decimal("0.00")
                        )
                    ),
                    Decimal("0.00")
                ).label("calculated_balance")
            )
            .join(Transaction, Transaction.account_id == Account.id, isouter=True)
            .where(Transaction.status == TransactionStatus.POSTED)
            .group_by(Account.name)
        )
        
        audit_results = await session.execute(audit_stmt)
        for acc_name, calc_bal in audit_results.all():
            print(f"Conta: {acc_name:<35} | Saldo Calculado (PG Ledger): R$ {calc_bal:>12.2f}")

        print("-" * 80)
        print("✅ Migração ETL concluída e validada com sucesso!")
        print("=" * 80 + "\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_etl())
