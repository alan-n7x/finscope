import openpyxl
import pathlib
import datetime

def main():
    target_path = pathlib.Path(r"C:\Users\ndala\OneDrive\Documentos\Financeiro\controle_financeiro.xlsx")
    print(f"Loading workbook: {target_path}")
    wb = openpyxl.load_workbook(target_path)
    ws = wb['Lancamentos']

    # Find last row with date in column 1
    last_row = 1
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=1).value is not None:
            last_row = r

    print(f"Last populated row in Lancamentos: {last_row}")

    new_transactions = [
        (datetime.datetime(2026, 8, 10, 0, 0), 'Despesa', 'Outros', 'SEGURO CARTAO', 'Débito automático', 10.71, 'Não', 'Sim', 'Seguro Cartão Itaú', '2026-08', 'Itaú - Conta corrente', None, None, None, None),
        (datetime.datetime(2026, 8, 12, 0, 0), 'Despesa', 'Outros', 'PIX TRANSF Ricardo12/08', 'Pix', 100.00, 'Não', 'Sim', 'Pix enviado Ricardo', '2026-08', 'Itaú - Conta corrente', None, None, None, None),
        (datetime.datetime(2026, 8, 12, 0, 0), 'Despesa', 'Outros', 'PIX QRS LUIZ PEREIR12/08', 'Pix', 10.00, 'Não', 'Sim', 'Pix QRS Luiz', '2026-08', 'Itaú - Conta corrente', None, None, None, None),
        (datetime.datetime(2026, 8, 13, 0, 0), 'Despesa', 'Outros', 'PIX QRS 65.034.307 13/08', 'Pix', 16.90, 'Não', 'Sim', 'Pix QRS', '2026-08', 'Itaú - Conta corrente', None, None, None, None),
        (datetime.datetime(2026, 8, 13, 0, 0), 'Despesa', 'Outros', 'PIX QRS PAGSEGURO I13/08', 'Pix', 7.49, 'Não', 'Sim', 'Pix Pagseguro', '2026-08', 'Itaú - Conta corrente', None, None, None, None),
        (datetime.datetime(2026, 8, 14, 0, 0), 'Despesa', 'Outros', 'PIX QRS 65.034.307 14/08', 'Pix', 18.50, 'Não', 'Sim', 'Pix QRS', '2026-08', 'Itaú - Conta corrente', None, None, None, None),
        (datetime.datetime(2026, 8, 14, 0, 0), 'Despesa', 'Alimentação', 'PIX QRS SHIGUEO SUP14/08', 'Pix', 29.00, 'Sim', 'Sim', 'Supermercado Shigueo', '2026-08', 'Itaú - Conta corrente', None, None, None, None),
    ]

    curr_r = last_row + 1
    for item in new_transactions:
        dt, tipo, cat, desc, forma, valor, ess, pago, obs, mes, conta, c_dest, id_parc, parc, id_rec = item
        ws.cell(row=curr_r, column=1, value=dt)
        ws.cell(row=curr_r, column=2, value=tipo)
        ws.cell(row=curr_r, column=3, value=cat)
        ws.cell(row=curr_r, column=4, value=desc)
        ws.cell(row=curr_r, column=5, value=forma)
        ws.cell(row=curr_r, column=6, value=valor)
        ws.cell(row=curr_r, column=7, value=ess)
        ws.cell(row=curr_r, column=8, value=pago)
        ws.cell(row=curr_r, column=9, value=obs)
        ws.cell(row=curr_r, column=10, value=mes)
        ws.cell(row=curr_r, column=11, value=f'=IF(B{curr_r}="Receita",F{curr_r},IF(B{curr_r}="Despesa",-F{curr_r},0))')
        ws.cell(row=curr_r, column=12, value=conta)
        ws.cell(row=curr_r, column=13, value=c_dest)
        ws.cell(row=curr_r, column=14, value=id_parc)
        ws.cell(row=curr_r, column=15, value=parc)
        ws.cell(row=curr_r, column=16, value=id_rec)
        curr_r += 1

    # Update bank balance in Contas sheet for Itaú - Conta corrente
    ws_contas = wb['Contas']
    for r in range(2, ws_contas.max_row + 1):
        if ws_contas.cell(row=r, column=1).value == 'Itaú - Conta corrente':
            ws_contas.cell(row=r, column=4, value=634.76)
            print(f"Updated Contas row {r} Itaú current balance to 634.76")

    wb.save(target_path)
    print(f"SUCCESS: Wrote {len(new_transactions)} transactions up to row {curr_r - 1} into {target_path}")

if __name__ == '__main__':
    main()
