"""Parser do extrato em PDF do Itaú (conta corrente).

O layout é identificado pelas linhas de lançamento no formato
`DD/MM/YYYY DESCRIÇÃO VALOR`, com `SALDO DO DIA` virando snapshot e o
"saldo em conta" do cabeçalho como snapshot mais recente.

A extração usa `page.extract_text()` porque o PDF do Itaú já entrega uma
linha por lançamento. Este módulo foi movido de `app/import_engine.py` sem
refatorar a extração (ver `docs/PARSERS.md`); a evolução para o modelo de
linhas visuais de `app.parsers.base` fica para quando houver um fixture
anonimizado do Itaú.
"""
from __future__ import annotations

import io
import re
from typing import List

import pdfplumber

from ..import_rules import (
    classify_transfer_type,
    is_self_transfer,
    stable_id,
    suggest_category,
)
from ..schemas import BalanceSnapshot, ImportTransaction
from .base import ParserResult

BANK = "Itaú - Conta corrente"

# Linha de lançamento: DD/MM/YYYY DESCRIÇÃO VALOR
TRANSACTION_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})"
)


def parse_pdf(file_bytes: bytes) -> ParserResult:
    """Interpreta o extrato em PDF do Itaú (conta corrente).

    Extrai lançamentos por regex de linha, linhas SALDO DO DIA como
    snapshots e o "saldo em conta" do cabeçalho como snapshot mais recente.

    Args:
        file_bytes: Conteúdo bruto do arquivo `.pdf` do Itaú.

    Returns:
        Tupla (transações, snapshots de saldo, "Itaú - Conta corrente").
    """
    transactions: List[ImportTransaction] = []
    snapshots: List[BalanceSnapshot] = []
    header_snapshot: BalanceSnapshot | None = None
    balance: float | None = None

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")
            for i, line in enumerate(lines):
                # Extract "saldo em conta" from header (first page only)
                if header_snapshot is None and "saldo em conta" in line.lower():
                    # Next line should contain the value: R$ 627,75 R$ 0,00 ...
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        val_match = re.search(r"R\$\s*([\d.]+,\d{2})", next_line)
                        if val_match:
                            balance_str = val_match.group(1).replace(".", "").replace(",", ".")
                            try:
                                balance = float(balance_str)
                            except ValueError:
                                balance = None

                # Extract emission date from header
                if header_snapshot is None and "emitido em:" in line.lower():
                    date_match = re.search(r"emitido em:\s*(\d{2}/\d{2}/\d{4})", line)
                    if date_match and balance is not None:
                        d, m, y = date_match.group(1).split("/")
                        iso_date = f"{y}-{m}-{d}"
                        header_snapshot = BalanceSnapshot(date=iso_date, balance=balance)

                match = TRANSACTION_RE.search(line)
                if not match:
                    continue

                date_str = match.group(1)
                desc = match.group(2).strip()
                val_str = match.group(3).replace(".", "").replace(",", ".")

                # Extract SALDO DO DIA lines as balance snapshots
                if "SALDO" in desc.upper() or "SDO" in desc.upper():
                    try:
                        snapshot_balance = float(val_str)
                        d, m, y = date_str.split("/")
                        snapshots.append(
                            BalanceSnapshot(
                                date=f"{y}-{m}-{d}",
                                balance=snapshot_balance,
                            )
                        )
                    except ValueError:
                        pass
                    continue

                try:
                    amount = float(val_str)
                except ValueError:
                    continue

                self_transfer = is_self_transfer(desc)
                t_type = classify_transfer_type(desc, amount)
                category = suggest_category(
                    desc, self_transfer, amount=amount, tx_type=t_type
                )
                amount = abs(amount)

                d, m, y = date_str.split("/")
                iso_date = f"{y}-{m}-{d}"

                tx_id = stable_id("itau", iso_date, f"{amount:.2f}", t_type, desc)

                transactions.append(
                    ImportTransaction(
                        id=tx_id,
                        date=iso_date,
                        type=t_type,
                        description=desc,
                        amount=amount,
                        status="NEW",
                        category=category,
                        account=BANK,
                    )
                )

    # Add header snapshot (saldo em conta) - this is the most recent and accurate
    if header_snapshot:
        # Remove any existing snapshot for the same date (from SALDO DO DIA)
        snapshots = [s for s in snapshots if s.date != header_snapshot.date]
        snapshots.append(header_snapshot)

    return transactions, snapshots, BANK
