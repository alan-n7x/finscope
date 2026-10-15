import hashlib
import io
import datetime
import pdfplumber
import re
from typing import List, Tuple
from ofxparse import OfxParser

from .schemas import ImportTransaction, BalanceSnapshot

SELF_TRANSFER_MARKERS = ("ALAN DO",)
ESTORNO_MARKERS = ("ESTORNO",)
DEFAULT_ITAU_ACCOUNT = "Itaú - Conta corrente"


def is_self_transfer(description: str) -> bool:
    """Detecta movimentação entre contas próprias (Itaú <-> Inter)."""
    desc = (description or "").upper()
    return any(m in desc for m in SELF_TRANSFER_MARKERS)


def suggest_category(description: str, is_self: bool) -> str:
    """Sugere categoria para o preview sem quebrar o contrato do frontend."""
    desc = (description or "").upper()
    if is_self:
        return "Transferência interna"
    if any(m in desc for m in ESTORNO_MARKERS):
        return "Estorno / Reembolso"
    return "Outros"


def classify_transfer_type(description: str, amount: float) -> str:
    """Classifica o tipo preservando a convenção do ledger e o dashboard.

    Convenção existente no banco e hipótese do dashboard
    (TRANSFER soma + só se a descrição contém 'recebido'):
    - self out (valor negativo / PAYMENT) -> Despesa (visível no gasto do mês);
    - self in com 'recebido' na descrição -> Transferência (ex.: Inter/Santander);
    - self in sem 'recebido' (ex.: Itaú 'PIX TRANSF ALAN DO') -> Receita
      com categoria 'Transferência interna' para não inverter o sinal.
    """
    if not is_self_transfer(description):
        return "Receita" if amount > 0 else "Despesa"
    if amount < 0:
        return "Despesa"
    if "RECEBIDO" in (description or "").upper():
        return "Transferência"
    return "Receita"


def stable_id(prefix: str, *parts: str) -> str:
    """Gera id determinístico para idempotência no re-upload."""
    raw = "|".join([prefix, *[str(p) for p in parts]])
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def resolve_import_account(payload_account: str | None, transactions: List[ImportTransaction]) -> str:
    """Resolve a conta do import sem fixar Itaú (retrocompatível)."""
    if payload_account and payload_account.strip():
        return payload_account.strip()
    for t in transactions:
        if t.account and t.account.strip():
            return t.account.strip()
    return DEFAULT_ITAU_ACCOUNT

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
        description = stmt.memo or stmt.payee or "Transação Genérica"
        self_transfer = is_self_transfer(description)
        t_type = classify_transfer_type(description, amount)
        amount = abs(amount)

        fitid = (getattr(stmt, "id", None) or "").strip()
        if fitid:
            tx_id = f"ofx-{fitid}"
        else:
            tx_id = stable_id("ofx", t_date, f"{amount:.2f}", t_type, description)

        t = ImportTransaction(
            id=tx_id,
            date=t_date,
            type=t_type,
            description=description,
            amount=amount,
            status="NEW",
            category=suggest_category(description, self_transfer),
            account=account_guess,
        )
        transactions.append(t)

    snapshots: List[BalanceSnapshot] = []
    try:
        balance = ofx.account.statement.balance
        balance_date = ofx.account.statement.balance_date
        if balance is not None and balance_date is not None:
            snapshots.append(BalanceSnapshot(
                date=balance_date.strftime("%Y-%m-%d"),
                balance=float(balance),
            ))
    except (AttributeError, ValueError, TypeError):
        pass

    return transactions, snapshots, account_guess

def parse_itau_pdf(file_bytes: bytes) -> Tuple[List[ImportTransaction], List[BalanceSnapshot], str]:
    """Parses an Itaú PDF bank statement."""
    transactions = []
    snapshots = []
    header_snapshot = None
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            for i, line in enumerate(lines):
                # Extract "saldo em conta" from header (first page only)
                if header_snapshot is None and "saldo em conta" in line.lower():
                    # Next line should contain the value: R$ 627,75 R$ 0,00 ...
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        val_match = re.search(r'R\$\s*([\d.]+,\d{2})', next_line)
                        if val_match:
                            balance_str = val_match.group(1).replace('.', '').replace(',', '.')
                            try:
                                balance = float(balance_str)
                            except ValueError:
                                balance = None
                
                # Extract emission date from header
                if header_snapshot is None and "emitido em:" in line.lower():
                    date_match = re.search(r'emitido em:\s*(\d{2}/\d{2}/\d{4})', line)
                    if date_match and balance is not None:
                        d, m, y = date_match.group(1).split('/')
                        iso_date = f"{y}-{m}-{d}"
                        header_snapshot = BalanceSnapshot(date=iso_date, balance=balance)

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

                    self_transfer = is_self_transfer(desc)
                    t_type = classify_transfer_type(desc, amount)
                    amount = abs(amount)
                    
                    # Convert DD/MM/YYYY to YYYY-MM-DD
                    d, m, y = date_str.split('/')
                    iso_date = f"{y}-{m}-{d}"

                    tx_id = stable_id("itau", iso_date, f"{amount:.2f}", t_type, desc)
                    
                    t = ImportTransaction(
                        id=tx_id,
                        date=iso_date,
                        type=t_type,
                        description=desc,
                        amount=amount,
                        status="NEW",
                        category=suggest_category(desc, self_transfer),
                        account="Itaú - Conta corrente",
                    )
                    transactions.append(t)
    
    # Add header snapshot (saldo em conta) - this is the most recent and accurate
    if header_snapshot:
        # Remove any existing snapshot for the same date (from SALDO DO DIA)
        snapshots = [s for s in snapshots if s.date != header_snapshot.date]
        snapshots.append(header_snapshot)
                    
    return transactions, snapshots, "Itaú - Conta corrente"

def reconcile_transactions(imported_txs: List[ImportTransaction], db_txs: List[dict]) -> List[ImportTransaction]:
    """
    Cross-checks imported transactions against existing DB transactions.
    db_txs should be a list of dictionaries with keys: 'date', 'amount', 'type', 'description'.
    Quando ambos os lados informam 'account', o match exige a mesma conta —
    sem isso, as duas pernas de uma transferência interna (Itaú out x Inter in,
    mesmo valor/data) geram falso MATCHED e uma perna deixa de ser importada.
    """
    for imp in imported_txs:
        imp_date = datetime.datetime.strptime(imp.date, "%Y-%m-%d").date()
        imp_account = (imp.account or "").strip().lower()
        
        match_found = False
        for db_t in db_txs:
            # Check if amounts match exactly
            if abs(db_t['amount'] - imp.amount) < 0.01 and db_t['type'] == imp.type:
                db_account = str(db_t.get('account') or "").strip().lower()
                if imp_account and db_account and imp_account != db_account:
                    continue
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
