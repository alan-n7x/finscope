"""Parser de extratos OFX (Inter, Santander, Nubank, Itaú...).

OFX é um formato estruturado: o FITID vira identidade estável, o LEDGERBAL
vira snapshot de saldo e os campos já chegam separados. Não há regex de layout
aqui — mudanças de banco normalmente não exigem alteração neste módulo.
"""
from __future__ import annotations

import io
from typing import List

from ofxparse import OfxParser

from ..import_rules import (
    classify_transfer_type,
    is_self_transfer,
    stable_id,
    suggest_category,
)
from ..schemas import BalanceSnapshot, ImportTransaction
from .base import ParserResult

def parse_ofx(file_bytes: bytes) -> ParserResult:
    """Interpreta um extrato OFX genérico.

    Usa o FITID como id estável do lançamento e o LEDGERBAL como snapshot
    de saldo; classifica transferências próprias e estornos.

    Args:
        file_bytes: Conteúdo bruto do arquivo `.ofx`.

    Returns:
        Tupla (transações, snapshots de saldo, palpite de conta destino).
    """
    ofx = OfxParser.parse(io.BytesIO(file_bytes))
    transactions: List[ImportTransaction] = []

    account_guess = _guess_account(ofx)

    for stmt in ofx.account.statement.transactions:
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

        transactions.append(
            ImportTransaction(
                id=tx_id,
                date=t_date,
                type=t_type,
                description=description,
                amount=amount,
                status="NEW",
                category=suggest_category(description, self_transfer),
                account=account_guess,
            )
        )

    snapshots: List[BalanceSnapshot] = []
    try:
        balance = ofx.account.statement.balance
        balance_date = ofx.account.statement.balance_date
        if balance is not None and balance_date is not None:
            snapshots.append(
                BalanceSnapshot(
                    date=balance_date.strftime("%Y-%m-%d"),
                    balance=float(balance),
                )
            )
    except (AttributeError, ValueError, TypeError):
        pass

    return transactions, snapshots, account_guess


def _guess_account(ofx) -> str | None:
    """Infere a conta pelo banco/FITID do cabeçalho OFX.

    Args:
        ofx: Objeto retornado por `OfxParser.parse`.

    Returns:
        Nome da conta conhecida ou None quando o banco não é reconhecido.
    """
    if not ofx.account:
        return None

    account_id = (ofx.account.account_id or "").upper()
    bank_id = ofx.account.routing_number or ""

    if "SANTANDER" in account_id or "033" in bank_id:
        return "Santander"
    if "INTER" in account_id or "077" in bank_id:
        return "Banco Inter - Conta corrente"
    if "ITAU" in account_id or "341" in bank_id:
        return "Itaú - Conta corrente"
    if "NUBANK" in account_id or "260" in bank_id:
        return "Nubank"
    return None
