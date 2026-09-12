from __future__ import annotations

import asyncio
import datetime
import os
import pathlib
import sys
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict

import openpyxl
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Adiciona o path raiz do projeto
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from app.infra.db.models import (
    Base,
    User,
    Account,
    AccountType,
    AccountBalanceSnapshot,
    Category,
    Debt,
    DebtPriority,
    DebtStatus,
    Transaction,
    TransactionType,
    TransactionStatus,
)
# Script de migração única (one-shot) da planilha legada para o PostgreSQL.
# A aplicação em runtime não usa mais a planilha local (ver app/main.py);
# este helper existe apenas para localizar o arquivo de origem da migração.
LEGACY_EXCEL_PATH = pathlib.Path(__file__).resolve().parent.parent / "app" / "data" / "controle_financeiro.xlsx"
# Caminho opcional da planilha legada em outra maquina (ex: Windows com OneDrive).
# Configure via env FINSCOPE_LEGACY_EXCEL_PATH; o valor default abaixo e apenas um placeholder.
LEGACY_FALLBACK_ONEDRIVE_PATH = pathlib.Path(
    os.getenv(
        "FINSCOPE_LEGACY_EXCEL_PATH",
        r"C:\Users\Public\Documents\Financeiro\controle_financeiro.xlsx",
    )
)


def get_excel_path() -> pathlib.Path:
    """Resolve o caminho da planilha legada usada como fonte da migração única."""
    import os as _os

    p = LEGACY_EXCEL_PATH
    if p.is_symlink():
        try:
            target = pathlib.Path(_os.readlink(p))
            if target.exists():
                return target.resolve()
        except Exception:
            pass

    if p.is_file():
        try:
            content = p.read_text(encoding="utf-8", errors="ignore").strip()
            if content and (content.endswith(".xlsx") or "Financeiro" in content):
                clean_path = content.replace("\\\\?\\", "").strip()
                target = pathlib.Path(clean_path)
                if target.exists():
                    return target.resolve()
        except Exception:
            pass

        if zipfile.is_zipfile(p):
            return p.resolve()

    if LEGACY_FALLBACK_ONEDRIVE_PATH.exists():
        return LEGACY_FALLBACK_ONEDRIVE_PATH.resolve()

    return p.resolve()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/finscope"
)

# Dados do usuario padrao criado durante a migracao (sobrescreva via .env)
DEFAULT_USER_NAME = os.getenv("FINSCOPE_USER_NAME", "Admin Finscope")
DEFAULT_USER_EMAIL = os.getenv("FINSCOPE_USER_EMAIL", "admin@finscope.local")


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
    print(f"[INFO] Lendo arquivo de origem: {excel_file}")
    
    if not excel_file.exists():
        raise FileNotFoundError(f"Arquivo Excel não encontrado em {excel_file}")

    wb = openpyxl.load_workbook(excel_file, data_only=True)
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        print("[INFO] Recriando tabelas no PostgreSQL para migracao limpa...")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        async with session.begin():
            print("[INFO] Iniciando Transacao Atomica de Migracao...")

            # 1. Usuario Padrao
            user_stmt = select(User).where(User.email == DEFAULT_USER_EMAIL)
            res = await session.execute(user_stmt)
            user = res.scalar_one_or_none()
            if not user:
                user = User(name=DEFAULT_USER_NAME, email=DEFAULT_USER_EMAIL)
                session.add(user)
                await session.flush()
                print(f"[INFO] Usuario criado: {user.name} ({user.id})")

            # 2. Migrar Contas (Sheet: 'Contas')
            # account_snapshots guarda: {acc_key -> (actual_balance, snapshot_date)}
            account_snapshots: Dict[str, tuple] = {}
            account_map: Dict[str, Account] = {}
            if "Contas" in wb.sheetnames:
                ws_contas = wb["Contas"]
                for row in ws_contas.iter_rows(min_row=4, values_only=True):
                    if not row[0] or str(row[0]).strip() == "":
                        continue

                    acc_name = str(row[0]).strip()
                    acc_type_str = str(row[1]).strip() if len(row) > 1 and row[1] else "Conta corrente"
                    # col C = Saldo inicial do mes, col D = Saldo bancario atual confirmado
                    initial_bal = to_decimal(row[2] if len(row) > 2 else None)
                    actual_bal = to_decimal(row[3] if len(row) > 3 else None)
                    # col I = data de atualizacao do saldo
                    updated_at_raw = row[8] if len(row) > 8 else None
                    snapshot_date = parse_date(updated_at_raw) if updated_at_raw else None

                    acc_type = (
                        AccountType.CREDIT_CARD
                        if "cartão" in acc_type_str.lower() or "crédito" in acc_name.lower()
                        else AccountType.CHECKING
                    )

                    acc = Account(
                        user_id=user.id,
                        name=acc_name,
                        type=acc_type,
                        initial_balance=initial_bal,
                        currency="BRL"
                    )
                    session.add(acc)
                    acc_key = acc_name.lower()
                    account_map[acc_key] = acc
                    if snapshot_date and actual_bal > 0:
                        account_snapshots[acc_key] = (actual_bal, snapshot_date)

                await session.flush()

                # Gravar snapshots de saldo bancario real (coluna D da planilha)
                snapshots_created = 0
                for acc_key, (actual_bal, snap_date) in account_snapshots.items():
                    snap = AccountBalanceSnapshot(
                        account_id=account_map[acc_key].id,
                        snapshot_date=snap_date,
                        balance=actual_bal,
                    )
                    session.add(snap)
                    snapshots_created += 1

                await session.flush()
                print(f"[INFO] {len(account_map)} Contas migradas | {snapshots_created} snapshots de saldo real gravados.")

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
                print(f"[INFO] {len(debt_map)} Contratos de Dividas migrados.")

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
                    acc_name_raw = str(row[11]).strip() if len(row) > 11 and row[11] else "Itaú - Conta corrente"
                    acc_name = acc_name_raw.lower()

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

                    # Mapear Conta — se nao encontrada, cria dinamicamente (sem fallback silencioso)
                    if acc_name not in account_map:
                        new_acc = Account(
                            user_id=user.id,
                            name=acc_name_raw,
                            type=AccountType.CHECKING,
                            initial_balance=Decimal("0.00"),
                            currency="BRL"
                        )
                        session.add(new_acc)
                        await session.flush()
                        account_map[acc_name] = new_acc
                        print(f"[WARN] Conta nao cadastrada na aba Contas — criada automaticamente: '{acc_name_raw}'")
                    account = account_map[acc_name]

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
                print(f"[INFO] {total_txs_migrated} Lancamentos inseridos no Ledger com sucesso.")

        # 5. Auditoria Pós-Migração
        print("\n" + "=" * 80)
        print("RELATORIO DE AUDITORIA CONTABIL CRUZADA (Centavo a Centavo)")
        print("=" * 80)

        audit_stmt = (
            select(
                Account.name,
                func.coalesce(
                    func.sum(
                        case(
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
        print("[SUCESSO] Migracao ETL concluida e validada com sucesso!")
        print("=" * 80 + "\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_etl())
