import sys
import os
sys.path.append(r"E:\Developer\finscope")

from app.excel_engine import add_transaction

months = ["2026-08-16", "2026-09-16", "2026-10-16", "2026-11-16", "2026-12-16"]

for d in months:
    is_current = d.startswith("2026-08")
    data = {
        "date": d,
        "type": "Despesa",
        "category": "Assinaturas",
        "description": "Spotify Premium",
        "payment_method": "Cartão de Crédito",
        "amount": 23.90,
        "essential": False,
        "paid": is_current,
        "account": "Itaú - Conta corrente"
    }
    res = add_transaction(data)
    print(f"Added {d}: {res['status']}")

print("All done!")
