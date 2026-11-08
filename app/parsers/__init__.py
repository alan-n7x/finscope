"""Registro de parsers de extrato e despacho por conteúdo do arquivo.

O endpoint de upload chama `parse_pdf`; a detecção é feita pelo próprio
conteúdo (não pelo nome do arquivo), e cada banco vive em um módulo isolado:

- `app.parsers.mercadopago`: PDF do Mercado Pago;
- `app.import_engine.parse_itau_pdf`: PDF do Itaú (parser legado, ainda fora
  do pacote — ver `docs/PARSERS.md`).

Adicionar um banco novo é criar `app/parsers/<banco>.py` com `detect` e
`parse_pages`, registrá-lo aqui e incluir um fixture em `tests/fixtures/`.
"""
from __future__ import annotations

from .. import import_engine
from . import mercadopago
from .base import ParserResult, StatementFormatError, read_pages

SUPPORTED_FORMATS = ("OFX", "PDF do Itaú", "PDF do Mercado Pago")

__all__ = ["SUPPORTED_FORMATS", "StatementFormatError", "parse_pdf"]


def parse_pdf(file_bytes: bytes) -> ParserResult:
    """Detecta o banco do PDF e delega ao parser correspondente.

    Args:
        file_bytes: Conteúdo bruto do `.pdf` enviado.

    Returns:
        Tupla `(transações, snapshots de saldo, palpite de conta)`.

    Raises:
        StatementFormatError: Quando o PDF não é reconhecido por nenhum parser
            ou quando os totais extraídos não fecham com o cabeçalho.
    """
    try:
        pages = read_pages(file_bytes)
    except Exception as exc:  # pdfminer levanta tipos variados para PDF inválido
        raise StatementFormatError(
            "Não foi possível ler o PDF (arquivo inválido, protegido ou corrompido)."
        ) from exc

    if mercadopago.detect(pages):
        return mercadopago.parse_pages(pages)

    # Comportamento retrocompatível: PDFs que não são do Mercado Pago seguem
    # para o parser do Itaú até a migração dele para este pacote.
    transactions, snapshots, account = import_engine.parse_itau_pdf(file_bytes)
    if not transactions and not snapshots:
        supported = ", ".join(SUPPORTED_FORMATS)
        raise StatementFormatError(
            "PDF não reconhecido por nenhum parser. "
            f"Formatos suportados hoje: {supported}. "
            "Se o layout do seu banco mudou, veja docs/PARSERS.md."
        )
    return transactions, snapshots, account
