import sys
import openpyxl
sys.path.append(r"E:\Developer\finscope")
from app.excel_engine import add_transaction, get_excel_path

txs = [
    {
        "date": "2026-08-29",
        "type": "Despesa",
        "category": "Transporte",
        "description": "Uber *TRIP HELP.U",
        "payment_method": "Cartão de Débito",
        "amount": 96.56,
        "essential": False,
        "paid": True,
        "account": "Banco Inter - Conta corrente"
    },
    {
        "date": "2026-08-29",
        "type": "Despesa",
        "category": "Alimentação",
        "description": "Supermercado Familia Lima",
        "payment_method": "Pix",
        "amount": 11.49,
        "essential": True,
        "paid": True,
        "account": "Banco Inter - Conta corrente"
    },
    {
        "date": "2026-08-30",
        "type": "Despesa",
        "category": "Transporte",
        "description": "Uber *TRIP HELP.U",
        "payment_method": "Cartão de Débito",
        "amount": 2.80,
        "essential": False,
        "paid": True,
        "account": "Banco Inter - Conta corrente"
    }
]

for t in txs:
    add_transaction(t)

# Fix inter balance just to be sure
target_path = get_excel_path()
wb = openpyxl.load_workbook(target_path)
ws = wb["Contas"]
for r in range(4, ws.max_row + 1):
    acc = ws.cell(row=r, column=1).value
    if acc:
        acc_str = str(acc).strip()
        if "Inter" in acc_str:
            ws.cell(row=r, column=4, value=88.66)

wb.save(target_path)
print("Updated successfully")
