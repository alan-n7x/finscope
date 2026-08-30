import sys
sys.path.append(r"E:\Developer\finscope")
from app.excel_engine import add_transaction

data = {
    "date": "2026-08-27",
    "type": "Despesa",
    "category": "Alimentação",  # Shigueo Supermercado is likely Alimentação
    "description": "Shigueo Supermercado",
    "payment_method": "Pix",
    "amount": 10.0,
    "essential": True,
    "paid": True,
    "account": "Banco Inter - Conta corrente"
}

res = add_transaction(data)
print(f"Added transaction: {res['status']}")
