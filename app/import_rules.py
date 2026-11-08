"""Regras de negócio compartilhadas pela importação de extratos.

Este módulo não lê arquivos: concentra classificação de transferências
próprias, sugestão de categoria, identidade estável, conciliação com o banco e
resolução da conta de destino. Os formatos de arquivo vivem em `app/parsers/`.
"""
from __future__ import annotations

import datetime
import hashlib
from typing import List

from .schemas import ImportTransaction

SELF_TRANSFER_MARKERS = ("ALAN DO",)
ESTORNO_MARKERS = ("ESTORNO",)
DEFAULT_ITAU_ACCOUNT = "Itaú - Conta corrente"


def is_self_transfer(description: str) -> bool:
    """Detecta movimentação entre contas próprias (Itaú <-> Inter).

    Args:
        description: Descrição do lançamento como veio do extrato.

    Returns:
        True quando a descrição indica transferência entre contas do
        próprio titular; False caso contrário.
    """
    desc = (description or "").upper()
    return any(m in desc for m in SELF_TRANSFER_MARKERS)


def suggest_category(description: str, is_self: bool) -> str:
    """Sugere categoria para o preview sem quebrar o contrato do frontend.

    Args:
        description: Descrição do lançamento como veio do extrato.
        is_self: Resultado de `is_self_transfer` para a descrição.

    Returns:
        "Transferência interna" para movimentação própria, "Estorno /
        Reembolso" para estornos e "Outros" nos demais casos.
    """
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

    Args:
        description: Descrição do lançamento como veio do extrato.
        amount: Valor com sinal (positivo = entrada, negativo = saída).

    Returns:
        "Despesa", "Receita" ou "Transferência" no padrão do preview de importação.
    """
    if not is_self_transfer(description):
        return "Receita" if amount > 0 else "Despesa"
    if amount < 0:
        return "Despesa"
    if "RECEBIDO" in (description or "").upper():
        return "Transferência"
    return "Receita"


def stable_id(prefix: str, *parts: str) -> str:
    """Gera id determinístico para idempotência no re-upload.

    Args:
        prefix: Origem do lançamento ("itau", "ofx", "mercadopago").
        *parts: Fragmentos que identificam o lançamento (data, valor, tipo,
            descrição ou o id nativo do banco).

    Returns:
        Identificador estável no formato "{prefix}-{sha1[:16]}"; o mesmo
        lançamento sempre gera o mesmo id entre uploads.
    """
    raw = "|".join([prefix, *[str(p) for p in parts]])
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def resolve_import_account(payload_account: str | None, transactions: List[ImportTransaction]) -> str:
    """Resolve a conta do import sem fixar Itaú (retrocompatível).

    Args:
        payload_account: Conta informada no topo do payload de confirmação, se houver.
        transactions: Lançamentos do preview, que já carregam `account` do parser.

    Returns:
        A conta do payload, ou a da primeira transação preenchida, ou o
        fallback "Itaú - Conta corrente" quando nada foi informado.
    """
    if payload_account and payload_account.strip():
        return payload_account.strip()
    for t in transactions:
        if t.account and t.account.strip():
            return t.account.strip()
    return DEFAULT_ITAU_ACCOUNT


def reconcile_transactions(imported_txs: List[ImportTransaction], db_txs: List[dict]) -> List[ImportTransaction]:
    """Cruza lançamentos importados com os existentes no banco.

    Marca MATCHED quando valor e tipo coincidem com tolerância de 2 dias;
    quando ambos os lados informam `account`, exige a mesma conta — sem
    isso, as duas pernas de uma transferência interna (Itaú out x Inter in,
    mesmo valor/data) geram falso MATCHED e uma perna deixa de ser importada.

    Args:
        imported_txs: Lançamentos vindos do parser (status atualizado in-place).
        db_txs: Lançamentos do banco como dicts com 'date', 'amount', 'type',
            'description' e, quando disponível, 'account'.

    Returns:
        A mesma lista de entrada, com `status` NEW ou MATCHED por item.
    """
    for imp in imported_txs:
        imp_date = datetime.datetime.strptime(imp.date, "%Y-%m-%d").date()
        imp_account = (imp.account or "").strip().lower()

        match_found = False
        for db_t in db_txs:
            if abs(db_t['amount'] - imp.amount) < 0.01 and db_t['type'] == imp.type:
                db_account = str(db_t.get('account') or "").strip().lower()
                if imp_account and db_account and imp_account != db_account:
                    continue
                db_date = datetime.datetime.strptime(db_t['date'], "%Y-%m-%d").date()
                diff = abs((db_date - imp_date).days)

                if diff <= 2:
                    imp.status = "MATCHED"
                    match_found = True
                    break

        if not match_found:
            imp.status = "NEW"

    return imported_txs
