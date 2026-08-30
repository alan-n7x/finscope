import sys
import re
import datetime
sys.path.append(r"E:\Developer\finscope")
from app.excel_engine import add_transaction, get_transactions

inter_text = """
27 de Julho de 2026 Saldo do dia: R$ 6,38 Valor Saldo por transação
Compra no debito: "No estabelecimento Uber UBER *TRIP HELP.U SAO PAULO BRA" -R$ 33,75 -R$ 28,62
Pix recebido: "Cp :90400888-ALAN DOS SANTOS OLIVEIRA" R$ 35,00 R$ 6,38
3 de Agosto de 2026 Saldo do dia: R$ 19,23
Compra no debito: "No estabelecimento Uber UBER *TRIP HELP.U" -R$ 27,25 -R$ 20,87
Pix recebido: "Cp :60701190-ALAN DOS SANTOS OLIVEIRA" R$ 30,00 R$ 9,13
Compra no debito: "No estabelecimento Uber UBER *TRIP HELP.U" -R$ 39,90 -R$ 30,77
Pix recebido: "Cp :60701190-ALAN DOS SANTOS OLIVEIRA" R$ 50,00 R$ 19,23
5 de Agosto de 2026 Saldo do dia: R$ 28,81
Estorno: "REF 2026-08-03 uber uber *trip help.u" R$ 3,38 R$ 22,61
Compra no debito: "No estabelecimento Uber UBER *TRIP HELP.U" -R$ 33,80 -R$ 11,19
Pix recebido: "Cp :90400888-ALAN DOS SANTOS OLIVEIRA" R$ 40,00 R$ 28,81
6 de Agosto de 2026 Saldo do dia: R$ 78,81
Estorno Compra cartao R$ 40,79 R$ 69,60
Compra no debito: "No estabelecimento Uber UBER *TRIP HELP.U" -R$ 40,79 R$ 28,81
Pix recebido: "Cp :60701190-ALAN DOS SANTOS OLIVEIRA" R$ 50,00 R$ 78,81
9 de Agosto de 2026 Saldo do dia: R$ 8,03
Pix enviado: "Cp :08561701-PAGSEGURO INTERNATIONAL" -R$ 8,90 R$ 69,91
Pix enviado: "Cp :19468242-IFOODCOM AGENCIA DE RESTAURANTES ONLINE SA" -R$ 61,88 R$ 8,03
24 de Agosto de 2026 Saldo do dia: R$ 428,03
Pix recebido: "Cp :60701190-ALAN DOS SANTOS OLIVEIRA" R$ 420,00 R$ 428,03
25 de Agosto de 2026 Saldo do dia: R$ 309,51
Compra no debito: "No estabelecimento Uber UBER *TRIP HELP.U" -R$ 43,52 R$ 384,51
Pix enviado: "Cp :90400888-Rogeris Nascimento Sobrinho" -R$ 75,00 R$ 309,51
"""

itau_text = """
25/08/2026 SALDO DO DIA 6,03
24/08/2026 RENEGOCIACAO ITAU 04/10 -7,79
24/08/2026 RENEGOCIACAO ITAU 04/10 -36,41
24/08/2026 RENEGOCIACAO ITAU 04/10 -63,86
24/08/2026 RENEGOCIACAO ITAU 04/10 -33,80
24/08/2026 PIX TRANSF ALAN DO24/08 -420,00
24/08/2026 REND PAGO APLIC AUT APR 0,04
24/08/2026 SALDO DO DIA 6,02
21/08/2026 PIX QRS 65.034.307 21/08 -16,90
21/08/2026 PIX TRANSF Ricardo21/08 -50,00
21/08/2026 SALDO DO DIA 567,84
14/08/2026 PIX QRS 65.034.307 14/08 -18,50
14/08/2026 PIX QRS SHIGUEO SUP14/08 -29,00
14/08/2026 SALDO DO DIA 634,74
13/08/2026 PIX QRS 65.034.307 13/08 -16,90
13/08/2026 PIX QRS PAGSEGURO I13/08 -7,49
13/08/2026 SALDO DO DIA 682,24
12/08/2026 PIX TRANSF Ricardo12/08 -100,00
12/08/2026 PIX QRS LUIZ PEREIR12/08 -10,00
12/08/2026 SALDO DO DIA 706,63
10/08/2026 PIX TRANSF LUCAS M08/08 -20,00
10/08/2026 PIX QRS 65.034.307 08/08 -12,00
10/08/2026 SEGURO CARTAO -10,71
10/08/2026 SALDO DO DIA 816,63
06/08/2026 PIX TRANSF ALAN DO06/08 -50,00
06/08/2026 SALDO DO DIA 859,34
05/08/2026 PIX TRANSF Jeffers05/08 -10,00
05/08/2026 PIX QRS PARATI - CR05/08 -139,79
05/08/2026 PIX QRS TIM S A05/08 -61,56
05/08/2026 SALDO DO DIA 909,34
04/08/2026 PIX TRANSF Alan Do04/08 -23,00
04/08/2026 SALDO DO DIA 1.120,69
03/08/2026 REMUNERACAO/SALARIO 2.332,24
03/08/2026 CRED CONSIGNAD -265,45
03/08/2026 PIX TRANSF Alan Do01/08 -100,00
03/08/2026 PIX TRANSF ROGERIS01/08 -75,00
03/08/2026 PIX TRANSF Jeffers01/08 -20,00
03/08/2026 PIX TRANSF Elber L01/08 -30,00
03/08/2026 SAQUE BANCO24H 989421022 -40,00
03/08/2026 PIX QRS 58.273.958 01/08 -4,00
03/08/2026 PIX QRS 58.562.866 01/08 -25,00
03/08/2026 PIX TRANSF Elber L01/08 -50,00
03/08/2026 SAQUE BANCO24H 767053595 -50,00
03/08/2026 PIX QRS RAISSA CARO01/08 -20,00
03/08/2026 PIX TRANSF Elber L02/08 -165,00
03/08/2026 PIX TRANSF ALAN DO03/08 -50,00
03/08/2026 PIX QRS SUPERSIM AN03/08 -147,42
03/08/2026 PIX TRANSF ALAN DO03/08 -30,00
03/08/2026 PIX QRS SHIGUEO SUP03/08 -16,00
03/08/2026 RENEGOCIA PARCIAL 03/10 -33,54
03/08/2026 RENEGOCIA PARCIAL 03/10 -63,65
03/08/2026 MULTA RENEGOCIACAO 03/10 -1,27
03/08/2026 MULTA RENEGOCIACAO 03/10 -0,67
03/08/2026 JUROS RENEGOCIACAO 03/10 -0,69
03/08/2026 JUROS RENEGOCIACAO 03/10 -0,86
03/08/2026 SALDO DO DIA 1.143,69
28/07/2026 PIX TRANSF ALAN DO28/07 50,00
28/07/2026 RENEGOCIACAO ITAU 03/10 -7,99
28/07/2026 RENEGOCIACAO ITAU 03/10 -37,52
28/07/2026 CRED CONSIGNAD -5,09
28/07/2026 SALDO DO DIA 0,00
23/07/2026 PIX TRANSF ALAN DO23/07 -20,00
23/07/2026 PIX QRS YOUSE VENDI23/07 -20,49
23/07/2026 PIX TRANSF ALAN DO23/07 -482,00
23/07/2026 REND PAGO APLIC AUT MAIS 0,05
23/07/2026 SALDO DO DIA 0,60
22/07/2026 PIX TRANSF Ricardo22/07 -50,00
22/07/2026 SALDO DO DIA 523,04
21/07/2026 PIX QRS 99 FOOD21/07 -34,61
21/07/2026 PIX QRS AUTOPASS S 21/07 -5,40
21/07/2026 PIX TRANSF ALAN DO21/07 -20,00
21/07/2026 SALDO DO DIA 573,04
20/07/2026 PIX QRS IFOOD.COM A18/07 -39,09
20/07/2026 SALDO DO DIA 633,05
17/07/2026 PIX TRANSF ALAN DO17/07 -40,00
17/07/2026 SALDO DO DIA 672,14
16/07/2026 PIX TRANSF VENTMEA16/07 13,22
16/07/2026 PIX QRS WMS SUPERME16/07 -10,99
16/07/2026 PIX QRS YOUSE VENDI16/07 -12,99
16/07/2026 PIX QRS AUTOPASS S 16/07 -10,80
16/07/2026 PIX QRS SHIGUEO SUP16/07 -10,00
16/07/2026 SALDO DO DIA 712,14
15/07/2026 PIX QRS LUIZ PEREIR15/07 -10,00
15/07/2026 PIX TRANSF Ricardo15/07 -50,00
15/07/2026 SALDO DO DIA 743,70
13/07/2026 PIX TRANSF DOUGLAS11/07 -21,00
13/07/2026 PIX TRANSF Elber L11/07 -10,00
13/07/2026 SALDO DO DIA 803,70
10/07/2026 SAQUE BANCO24H 227692417 -50,00
10/07/2026 PIX TRANSF Elber L09/07 -20,00
10/07/2026 SEGURO CARTAO -10,71
10/07/2026 SALDO DO DIA 834,70
08/07/2026 PIX TRANSF ALAN DO08/07 -50,00
08/07/2026 PIX TRANSF ALAN DO08/07 -50,00
08/07/2026 PIX TRANSF ROGERIS08/07 -75,00
08/07/2026 SALDO DO DIA 915,41
07/07/2026 PIX TRANSF ALAN DO07/07 -50,00
07/07/2026 DESPESA COBR JUN/26 -0,75
07/07/2026 SALDO DO DIA 1.090,41
06/07/2026 PIX TRANSF Ricardo06/07 -100,00
06/07/2026 SALDO DO DIA 1.141,16
06/07/2026 PIX QRS SAFE2PAY IN06/07 -4,99
02/07/2026 PIX QRS FACIO PAGAM02/07 -205,19
02/07/2026 PIX TRANSF ALAN DO02/07 -40,00
02/07/2026 PIX TRANSF ALAN DO02/07 -50,00
02/07/2026 SALDO DO DIA 1.246,15
01/07/2026 REMUNERACAO/SALARIO 2.336,09
01/07/2026 RENEGOCIACAO ITAU 02/10 -8,02
01/07/2026 RENEGOCIACAO ITAU 02/10 -37,71
01/07/2026 RENEGOCIACAO ITAU 02/10 -65,54
01/07/2026 RENEGOCIACAO ITAU 02/10 -34,98
01/07/2026 CRED CONSIGNAD -270,21
01/07/2026 PIX TRANSF ALAN DO01/07 -50,00
01/07/2026 PAG BOLETO JEITTO PAGAMENTOS -122,45
01/07/2026 PIX QRS TIM S A01/07 -59,99
01/07/2026 PIX QRS TIM S A01/07 -61,57
01/07/2026 PIX TRANSF ALAN DO01/07 -25,00
01/07/2026 PIX QRS NIC. BR01/07 -40,00
01/07/2026 PIX QRS SUPERSIM AN01/07 -69,42
01/07/2026 PIX TRANSF BMP SOC01/07 100,00
01/07/2026 PIX TRANSF ALAN DO01/07 -50,00
01/07/2026 SALDO DO DIA 1.541,34
"""

new_txs = []
months = {"Janeiro": "01", "Fevereiro": "02", "Março": "03", "Abril": "04", "Maio": "05", "Junho": "06", "Julho": "07", "Agosto": "08", "Setembro": "09", "Outubro": "10", "Novembro": "11", "Dezembro": "12"}

current_inter_date = None
for line in inter_text.strip().split("\n"):
    m = re.match(r'^(\d{1,2}) de ([A-Za-zç]+) de (\d{4})', line)
    if m:
        day = m.group(1).zfill(2)
        month = months.get(m.group(2), "01")
        year = m.group(3)
        current_inter_date = f"{year}-{month}-{day}"
        continue
    
    if "Saldo do dia" in line:
        continue
        
    m2 = re.search(r'(.+?)\s+(-?R\$\s*\d+,\d{2})', line)
    if m2 and current_inter_date:
        desc = m2.group(1).strip()
        val_str = m2.group(2).replace('R$', '').strip().replace('.', '').replace(',', '.')
        try:
            amount = float(val_str)
            t_type = "Receita" if amount > 0 else "Despesa"
            new_txs.append({
                "date": current_inter_date,
                "type": t_type,
                "description": desc,
                "amount": abs(amount),
                "account": "Banco Inter - Conta corrente",
                "payment_method": "Pix" if "Pix" in desc else "Cartão de Crédito",
                "paid": True
            })
        except ValueError:
            pass

for line in itau_text.strip().split("\n"):
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})\s+(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})', line)
    if m:
        d, month, y = m.group(1), m.group(2), m.group(3)
        desc = m.group(4).strip()
        if "SALDO DO DIA" in desc:
            continue
        val_str = m.group(5).replace('.', '').replace(',', '.')
        try:
            amount = float(val_str)
            t_type = "Receita" if amount > 0 else "Despesa"
            new_txs.append({
                "date": f"{y}-{month}-{d}",
                "type": t_type,
                "description": desc,
                "amount": abs(amount),
                "account": "Itaú - Conta corrente",
                "payment_method": "Pix" if "PIX" in desc else "Pix",
                "paid": True
            })
        except ValueError:
            pass

# Check against existing transactions to prevent duplicates
existing = get_transactions(limit=1000)
added_count = 0

def is_duplicate(tx):
    for e in existing:
        if e['date'] == tx['date'] and e['type'] == tx['type'] and abs(e['amount'] - tx['amount']) < 0.01 and e['account'] == tx['account']:
            # Maybe check description similarity but this is usually enough for a short time frame
            return True
    return False

for tx in new_txs:
    if not is_duplicate(tx):
        add_transaction(tx)
        added_count += 1

print(f"Successfully added {added_count} new transactions out of {len(new_txs)} extracted.")
