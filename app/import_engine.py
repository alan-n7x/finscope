import io
import datetime
import uuid
import pdfplumber
import re
from typing import List, Tuple
from ofxparse import OfxParser

from .schemas import ImportTransaction, BalanceSnapshot

def parse_ofx(file_bytes: bytes) -> Tuple[List[ImportTransaction], List[BalanceSnapshot], str]:
    """Parses OFX file and returns a list of transactions, balance snapshots, and account guess."""
    ofx = OfxParser.parse(io.BytesIO(file_bytes))
    transactions = []
    
    account_guess = None
    if ofx.account:
        account_id = ofx.account.account_id or ""
        bank_id = ofx.account.routing_number or ""
        if "033" in bank_id or "SANTANDER" in account_id.upper():
            account_guess = "Santander"
        elif "077" in bank_id or "INTER" in account_id.upper():
            account_guess = "Banco Inter - Conta corrente"
        elif "341" in bank_id or "ITAU" in account_id.upper():
            account_guess = "Itaú - Conta corrente"
        elif "NUBANK" in account_id.upper() or "260" in bank_id:
            account_guess = "Nubank"

    for stmt in ofx.account.statement.transactions:
        # Convert date
        t_date = stmt.date.strftime("%Y-%m-%d")
        amount = float(stmt.amount)
        t_type = "Receita" if amount > 0 else "Despesa"
        amount = abs(amount)

        t = ImportTransaction(
            id=str(uuid.uuid4()),
            date=t_date,
            type=t_type,
            description=stmt.memo or stmt.payee or "Transação Genérica",
            amount=amount,
            status="NEW"
        )
        transactions.append(t)
        
    return transactions, [], account_guess

def parse_itau_pdf(file_bytes: bytes) -> Tuple[List[ImportTransaction], List[BalanceSnapshot], str]:
    """Parses an Itaú PDF bank statement."""
    transactions = []
    snapshots = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            for line in lines:
                # Regex for Itaú line: DD/MM/YYYY DESCRIPTION VALUE
                # Example: 14/08/2026 PIX QRS 65.034.307 14/08 -18,50
                match = re.search(r'^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})', line)
                if match:
                    date_str = match.group(1)
                    desc = match.group(2).strip()
                    val_str = match.group(3).replace('.', '').replace(',', '.')
                    
                    # Extract SALDO DO DIA lines as balance snapshots
                    if "SALDO" in desc.upper() or "SDO" in desc.upper():
                        try:
                            balance = float(val_str)
                            d, m, y = date_str.split('/')
                            iso_date = f"{y}-{m}-{d}"
                            snapshots.append(BalanceSnapshot(
                                date=iso_date,
                                balance=balance,
                            ))
                        except ValueError:
                            pass
                        continue
                        
                    try:
                        amount = float(val_str)
                    except ValueError:
                        continue
                        
                    t_type = "Receita" if amount > 0 else "Despesa"
                    amount = abs(amount)
                    
                    # Convert DD/MM/YYYY to YYYY-MM-DD
                    d, m, y = date_str.split('/')
                    iso_date = f"{y}-{m}-{d}"
                    
                    t = ImportTransaction(
                        id=str(uuid.uuid4()),
                        date=iso_date,
                        type=t_type,
                        description=desc,
                        amount=amount,
                        status="NEW"
                    )
                    transactions.append(t)
                    
    return transactions, snapshots, "Itaú - Conta corrente"

def reconcile_transactions(imported_txs: List[ImportTransaction], db_txs: List[dict]) -> List[ImportTransaction]:
    """
    Cross-checks imported transactions against existing DB transactions.
    db_txs should be a list of dictionaries with keys: 'date', 'amount', 'type', 'description'.
    """
    for imp in imported_txs:
        imp_date = datetime.datetime.strptime(imp.date, "%Y-%m-%d").date()
        
        match_found = False
        for db_t in db_txs:
            # Check if amounts match exactly
            if abs(db_t['amount'] - imp.amount) < 0.01 and db_t['type'] == imp.type:
                # Check if dates are within 2 days
                db_date = datetime.datetime.strptime(db_t['date'], "%Y-%m-%d").date()
                diff = abs((db_date - imp_date).days)
                
                if diff <= 2:
                    imp.status = "MATCHED"
                    match_found = True
                    break
        
        if not match_found:
            imp.status = "NEW"
            
    return imported_txs
