import sys
import openpyxl
sys.path.append(r"E:\Developer\finscope")
from app.excel_engine import get_excel_path

target_path = get_excel_path()
wb = openpyxl.load_workbook(target_path)
ws = wb["Contas"]

# Rows start at 4 based on get_dashboard_summary logic
for r in range(4, ws.max_row + 1):
    acc = ws.cell(row=r, column=1).value
    if acc:
        acc_str = str(acc).strip()
        if "Itaú" in acc_str or "Ita" in acc_str:
            ws.cell(row=r, column=4, value=6.03)
        elif "Inter" in acc_str:
            ws.cell(row=r, column=4, value=309.51)

wb.save(target_path)
print("Balances fixed!")
