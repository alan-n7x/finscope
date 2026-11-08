"""Shim de compatibilidade da importação de extratos.

O código foi separado em dois módulos:

- `app.import_rules`: regras de negócio (classificação, id estável, conta,
  conciliação);
- `app.parsers`: leitura dos formatos, um módulo por banco.

Este arquivo mantém os nomes antigos (`parse_ofx`, `parse_itau_pdf`,
`reconcile_transactions`, ...) para não quebrar `scratch/*.py` e imports
externos. Código novo deve importar direto de `app.import_rules` e
`app.parsers`.
"""
from __future__ import annotations

from .import_rules import (
    DEFAULT_ITAU_ACCOUNT,
    ESTORNO_MARKERS,
    SELF_TRANSFER_MARKERS,
    classify_transfer_type,
    is_self_transfer,
    reconcile_transactions,
    resolve_import_account,
    stable_id,
    suggest_category,
)
from .parsers.itau import parse_pdf as parse_itau_pdf
from .parsers.ofx import parse_ofx

__all__ = [
    "DEFAULT_ITAU_ACCOUNT",
    "ESTORNO_MARKERS",
    "SELF_TRANSFER_MARKERS",
    "classify_transfer_type",
    "is_self_transfer",
    "parse_itau_pdf",
    "parse_ofx",
    "reconcile_transactions",
    "resolve_import_account",
    "stable_id",
    "suggest_category",
]
