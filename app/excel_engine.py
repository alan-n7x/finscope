import pathlib
import datetime
from typing import Any
import openpyxl

EXCEL_PATH = pathlib.Path(__file__).resolve().parent / "data" / "database.xlsx"


def get_excel_path() -> pathlib.Path:
    """Returns the resolved path of the Excel spreadsheet (following symlinks)."""
    return EXCEL_PATH.resolve()


def load_workbook(data_only: bool = True) -> openpyxl.Workbook:
    path = get_excel_path()
    return openpyxl.load_workbook(path, data_only=data_only)


def get_filter_options() -> dict[str, Any]:
    wb = load_workbook(data_only=True)
    
    categories: set[str] = set()
    payment_methods: set[str] = set()
    accounts: set[str] = set()
    months: set[str] = set()

    if "Lancamentos" in wb.sheetnames:
        ws = wb["Lancamentos"]
        rows = list(ws.iter_rows(values_only=True))
        for r in rows[1:]:
            if r[0] is not None:
                if len(r) > 2 and r[2]:
                    categories.add(str(r[2]).strip())
                if len(r) > 4 and r[4]:
                    payment_methods.add(str(r[4]).strip())
                if len(r) > 11 and r[11]:
                    accounts.add(str(r[11]).strip())
                if len(r) > 9 and r[9]:
                    months.add(str(r[9]).strip())
                elif isinstance(r[0], (datetime.datetime, datetime.date)):
                    months.add(r[0].strftime("%Y-%m"))

    return {
        "categories": sorted(list(categories)),
        "payment_methods": sorted(list(payment_methods)),
        "accounts": sorted(list(accounts)),
        "months": sorted(list(months), reverse=True),
        "types": ["Despesa", "Receita", "Transferência"],
    }


def get_dashboard_summary(month: str | None = None) -> dict[str, Any]:
    wb = load_workbook(data_only=True)
    
    # 1. Accounts & Balances
    accounts_list: list[dict[str, Any]] = []
    total_balance = 0.0
    if "Contas" in wb.sheetnames:
        ws_contas = wb["Contas"]
        rows = list(ws_contas.iter_rows(values_only=True))
        for r in rows[3:]:
            if r[0] and str(r[0]).strip():
                acc_name = str(r[0]).strip()
                acc_type = str(r[1]).strip() if len(r) > 1 and r[1] else "Conta"
                bal_val = 0.0
                try:
                    bal_val = float(r[3]) if len(r) > 3 and r[3] is not None else 0.0
                except (ValueError, TypeError):
                    bal_val = 0.0
                
                accounts_list.append({
                    "name": acc_name,
                    "type": acc_type,
                    "balance": round(bal_val, 2)
                })
                total_balance += bal_val

    # 2. Month transactions summary (Receitas, Despesas, Saldo do Mês)
    income_month = 0.0
    expense_month = 0.0
    
    target_month = month or datetime.date.today().strftime("%Y-%m")
    
    if "Lancamentos" in wb.sheetnames:
        ws = wb["Lancamentos"]
        rows = list(ws.iter_rows(values_only=True))
        for r in rows[1:]:
            if r[0] is not None:
                # Check month
                m_str = None
                if len(r) > 9 and r[9]:
                    m_str = str(r[9]).strip()
                elif isinstance(r[0], (datetime.datetime, datetime.date)):
                    m_str = r[0].strftime("%Y-%m")
                
                if m_str == target_month:
                    t_type = str(r[1]).strip() if len(r) > 1 and r[1] else ""
                    val = 0.0
                    try:
                        val = float(r[5]) if len(r) > 5 and r[5] is not None else 0.0
                    except (ValueError, TypeError):
                        val = 0.0
                    
                    if t_type == "Receita":
                        income_month += val
                    elif t_type == "Despesa":
                        expense_month += val

    # 3. Projections & Reserve from Painel/Premissas
    reserve_min = 310.0
    projected_final = total_balance + income_month - expense_month
    free_after_reserve = projected_final - reserve_min

    return {
        "month": target_month,
        "total_balance": round(total_balance, 2),
        "income_month": round(income_month, 2),
        "expense_month": round(expense_month, 2),
        "net_month": round(income_month - expense_month, 2),
        "projected_final": round(projected_final, 2),
        "reserve_min": round(reserve_min, 2),
        "free_after_reserve": round(free_after_reserve, 2),
        "accounts": accounts_list,
    }


def get_transactions(
    month: str | None = None,
    category: str | None = None,
    search: str | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    wb = load_workbook(data_only=True)
    transactions: list[dict[str, Any]] = []

    if "Lancamentos" not in wb.sheetnames:
        return transactions

    ws = wb["Lancamentos"]
    rows = list(ws.iter_rows(values_only=True))
    
    for row_idx, r in enumerate(rows[1:], start=2):
        if r[0] is None:
            continue

        d_val = r[0]
        if isinstance(d_val, (datetime.datetime, datetime.date)):
            d_str = d_val.strftime("%Y-%m-%d")
            m_str = d_val.strftime("%Y-%m")
        else:
            d_str = str(d_val)[:10]
            m_str = d_str[:7]

        if len(r) > 9 and r[9]:
            m_str = str(r[9]).strip()

        # Filters
        if month and m_str != month:
            continue

        t_type = str(r[1]).strip() if len(r) > 1 and r[1] else "Despesa"
        t_cat = str(r[2]).strip() if len(r) > 2 and r[2] else "Outros"
        t_desc = str(r[3]).strip() if len(r) > 3 and r[3] else ""
        t_payment = str(r[4]).strip() if len(r) > 4 and r[4] else ""
        
        try:
            t_amount = float(r[5]) if len(r) > 5 and r[5] is not None else 0.0
        except (ValueError, TypeError):
            t_amount = 0.0

        t_essential = str(r[6]).strip() if len(r) > 6 and r[6] else "Não"
        t_paid = str(r[7]).strip() if len(r) > 7 and r[7] else "Sim"
        t_obs = str(r[8]).strip() if len(r) > 8 and r[8] else ""
        t_account = str(r[11]).strip() if len(r) > 11 and r[11] else "Itaú - Conta corrente"

        if category and t_cat.lower() != category.lower():
            continue

        if status and t_paid.lower() != status.lower():
            continue

        if search:
            q = search.lower()
            if q not in t_desc.lower() and q not in t_cat.lower() and q not in t_account.lower():
                continue

        transactions.append({
            "id": row_idx,
            "date": d_str,
            "month": m_str,
            "type": t_type,
            "category": t_cat,
            "description": t_desc,
            "payment_method": t_payment,
            "amount": round(t_amount, 2),
            "essential": t_essential,
            "paid": t_paid,
            "obs": t_obs,
            "account": t_account,
        })

    # Sort descending by date
    transactions.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    return transactions[:limit]


def add_transaction(data: dict[str, Any]) -> dict[str, Any]:
    target_path = get_excel_path()
    wb = openpyxl.load_workbook(target_path)
    ws = wb["Lancamentos"]

    # Find next available row
    last_row = 1
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=1).value is not None:
            last_row = r

    next_row = last_row + 1

    # Parse date
    d_input = data.get("date")
    if isinstance(d_input, str):
        try:
            dt = datetime.datetime.strptime(d_input, "%Y-%m-%d")
        except ValueError:
            dt = datetime.datetime.now()
    elif isinstance(d_input, datetime.date):
        dt = datetime.datetime.combine(d_input, datetime.time.min)
    else:
        dt = datetime.datetime.now()

    month_str = dt.strftime("%Y-%m")
    t_type = data.get("type", "Despesa")
    t_cat = data.get("category", "Outros")
    t_desc = data.get("description", "")
    t_payment = data.get("payment_method", "Pix")
    t_amount = float(data.get("amount", 0.0))
    t_essential = "Sim" if data.get("essential", False) else "Não"
    t_paid = "Sim" if data.get("paid", True) else "Não"
    t_obs = data.get("obs", "")
    t_account = data.get("account", "Itaú - Conta corrente")

    ws.cell(row=next_row, column=1, value=dt)
    ws.cell(row=next_row, column=2, value=t_type)
    ws.cell(row=next_row, column=3, value=t_cat)
    ws.cell(row=next_row, column=4, value=t_desc)
    ws.cell(row=next_row, column=5, value=t_payment)
    ws.cell(row=next_row, column=6, value=t_amount)
    ws.cell(row=next_row, column=7, value=t_essential)
    ws.cell(row=next_row, column=8, value=t_paid)
    ws.cell(row=next_row, column=9, value=t_obs)
    ws.cell(row=next_row, column=10, value=month_str)
    ws.cell(
        row=next_row,
        column=11,
        value=f'=IF(B{next_row}="Receita",F{next_row},IF(B{next_row}="Despesa",-F{next_row},0))'
    )
    ws.cell(row=next_row, column=12, value=t_account)

    # Update account balance in Contas sheet if paid
    if t_paid == "Sim" and "Contas" in wb.sheetnames:
        ws_contas = wb["Contas"]
        for r in range(4, ws_contas.max_row + 1):
            cell_acc = ws_contas.cell(row=r, column=1).value
            if cell_acc and str(cell_acc).strip().lower() == t_account.lower():
                curr_bal = ws_contas.cell(row=r, column=4).value or 0.0
                try:
                    curr_bal = float(curr_bal)
                except (ValueError, TypeError):
                    curr_bal = 0.0

                if t_type == "Receita":
                    new_bal = curr_bal + t_amount
                elif t_type == "Despesa":
                    new_bal = curr_bal - t_amount
                else:
                    new_bal = curr_bal

                ws_contas.cell(row=r, column=4, value=round(new_bal, 2))
                break

    wb.save(target_path)
    return {
        "id": next_row,
        "date": dt.strftime("%Y-%m-%d"),
        "month": month_str,
        "type": t_type,
        "category": t_cat,
        "description": t_desc,
        "payment_method": t_payment,
        "amount": round(t_amount, 2),
        "essential": t_essential,
        "paid": t_paid,
        "account": t_account,
        "status": "success",
    }


def get_debts_summary() -> list[dict[str, Any]]:
    wb = load_workbook(data_only=True)
    debts: list[dict[str, Any]] = []

    if "Dividas" in wb.sheetnames:
        ws = wb["Dividas"]
        rows = list(ws.iter_rows(values_only=True))
        for r in rows[2:]:
            if r[0] and str(r[0]).strip():
                creditor = str(r[0]).strip()
                d_type = str(r[1]).strip() if len(r) > 1 and r[1] else "Outros"
                try:
                    balance = float(r[2]) if len(r) > 2 and r[2] is not None else 0.0
                    installment = float(r[3]) if len(r) > 3 and r[3] is not None else 0.0
                except (ValueError, TypeError):
                    balance = 0.0
                    installment = 0.0
                
                due_date = str(r[5])[:10] if len(r) > 5 and r[5] else ""
                priority = str(r[6]).strip() if len(r) > 6 and r[6] else "Média"
                status = str(r[7]).strip() if len(r) > 7 and r[7] else "Ativa"

                debts.append({
                    "creditor": creditor,
                    "type": d_type,
                    "balance": round(balance, 2),
                    "installment": round(installment, 2),
                    "due_date": due_date,
                    "priority": priority,
                    "status": status,
                })
    return debts
