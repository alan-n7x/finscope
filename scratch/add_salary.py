import sys
import os
sys.path.append(r"E:\Developer\finscope")

from app.excel_engine import add_transaction

data = {
    "date": "2026-09-04",
    "type": "Receita",
    "category": "Salário",
    "description": "REMUNERACAO/SALARIO",
    "payment_method": "Pix",
    "amount": 2332.24,
    "essential": True,
    "paid": False,  # Not paid yet as it's for next month
    "obs": "Projeção de salário baseada em Agosto",
    "account": "Itaú - Conta corrente"
}

res = add_transaction(data)
print(f"Added salary for Sept: {res['status']}")
