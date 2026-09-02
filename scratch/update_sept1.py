import sys
import openpyxl
sys.path.append(r"E:\Developer\finscope")
from app.excel_engine import add_transaction, get_excel_path

txs = [
    {
        "date": "2026-09-01",
        "type": "Receita",
        "category": "Salário",
        "description": "REMUNERACAO/SALARIO",
        "payment_method": "Pix",
        "amount": 2331.79,
        "essential": True,
        "paid": True,
        "account": "Itaú - Conta corrente"
    },
    {
        "date": "2026-09-01",
        "type": "Despesa",
        "category": "Dívidas",
        "description": "CRED CONSIGNAD",
        "payment_method": "Débito Automático",
        "amount": 264.36,
        "essential": True,
        "paid": True,
        "account": "Itaú - Conta corrente"
    },
    {
        "date": "2026-09-01",
        "type": "Despesa",
        "category": "Dívidas",
        "description": "PIX QRS JEITTO FUND01/09",
        "payment_method": "Pix",
        "amount": 392.52,
        "essential": True,
        "paid": True,
        "account": "Itaú - Conta corrente"
    },
    {
        "date": "2026-09-01",
        "type": "Despesa",
        "category": "Telefone",
        "description": "PIX QRS TIM S A01/09",
        "payment_method": "Pix",
        "amount": 59.99,
        "essential": True,
        "paid": True,
        "account": "Itaú - Conta corrente"
    },
    {
        "date": "2026-09-01",
        "type": "Transferência",
        "category": "Outros",
        "description": "PIX TRANSF ALAN DO01/09",
        "payment_method": "Pix",
        "amount": 100.00,
        "essential": False,
        "paid": True,
        "account": "Itaú - Conta corrente"
    },
    {
        "date": "2026-09-01",
        "type": "Transferência",
        "category": "Outros",
        "description": "PIX TRANSF Alan Do01/09",
        "payment_method": "Pix",
        "amount": 89.00,
        "essential": False,
        "paid": True,
        "account": "Itaú - Conta corrente"
    }
]

for t in txs:
    add_transaction(t)

# Fix itaú balance based on pdf
target_path = get_excel_path()
wb = openpyxl.load_workbook(target_path)
ws = wb["Contas"]
for r in range(4, ws.max_row + 1):
    acc = ws.cell(row=r, column=1).value
    if acc:
        acc_str = str(acc).strip()
        if "Ita" in acc_str or "Itaú" in acc_str:
            ws.cell(row=r, column=4, value=1425.91)
        elif "Mercado Pago" in acc_str:
            ws.cell(row=r, column=4, value=5.26)

wb.save(target_path)
print("Updated sept 1st successfully")
