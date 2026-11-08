"""Registro de parsers de extrato e despacho por tipo de arquivo.

O endpoint de upload chama `parse_statement`; a detecção do PDF é feita pelo
próprio conteúdo (não pelo nome do arquivo) e cada banco vive em um módulo
isolado:

- `app.parsers.ofx`: OFX genérico (Inter, Santander, Nubank, Itaú...);
- `app.parsers.itau`: PDF do Itaú (conta corrente);
- `app.parsers.mercadopago`: PDF do Mercado Pago.

Adicionar um banco novo é criar `app/parsers/<banco>.py` com `detect` e
`parse_pages` (ou `parse_pdf`, se precisar do binário), registrá-lo aqui e
incluir um fixture em `tests/fixtures/`. Passo a passo em `docs/PARSERS.md`.
"""
from __future__ import annotations

from typing import Final

from . import itau, mercadopago, ofx
from .base import (
    ParserResult,
    StatementFormatError,
    UnsupportedFileFormatError,
    read_pages,
)

SUPPORTED_FORMATS: Final = ("OFX", "PDF do Itaú", "PDF do Mercado Pago")
OFX_EXTENSIONS: Final = (".ofx",)
PDF_EXTENSIONS: Final = (".pdf",)

__all__ = [
    "SUPPORTED_FORMATS",
    "StatementFormatError",
    "UnsupportedFileFormatError",
    "parse_pdf",
    "parse_statement",
]


def parse_statement(filename: str | None, content: bytes) -> ParserResult:
    """Despacha o arquivo para o parser certo pelo tipo/extensão.

    Args:
        filename: Nome original enviado no upload (usado só para a extensão).
        content: Conteúdo bruto do arquivo.

    Returns:
        Tupla `(transações, snapshots de saldo, palpite de conta)`.

    Raises:
        UnsupportedFileFormatError: Quando a extensão não é OFX nem PDF.
        StatementFormatError: Quando o PDF não é reconhecido por nenhum parser
            ou quando os totais extraídos não fecham com o cabeçalho.
    """
    extension = _extension_of(filename)

    if extension in OFX_EXTENSIONS:
        return ofx.parse_ofx(content)
    if extension in PDF_EXTENSIONS:
        return parse_pdf(content)

    supported = ", ".join(SUPPORTED_FORMATS)
    raise UnsupportedFileFormatError(
        f"Formato não suportado ({extension or 'sem extensão'}). "
        f"Envie um destes formatos: {supported}."
    )


def parse_pdf(file_bytes: bytes) -> ParserResult:
    """Detecta o banco do PDF e delega ao parser correspondente.

    O Mercado Pago tem marcadores próprios; qualquer outro PDF segue para o
    parser do Itaú, que historicamente é o fallback do upload.

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

    transactions, snapshots, account = itau.parse_pdf(file_bytes)
    if not transactions and not snapshots:
        supported = ", ".join(SUPPORTED_FORMATS)
        raise StatementFormatError(
            "PDF não reconhecido por nenhum parser. "
            f"Formatos suportados hoje: {supported}. "
            "Se o layout do seu banco mudou, veja docs/PARSERS.md."
        )
    return transactions, snapshots, account


def _extension_of(filename: str | None) -> str:
    """Extrai a extensão em minúsculas, incluindo o ponto."""
    if not filename:
        return ""
    name = filename.strip().lower()
    dot = name.rfind(".")
    return name[dot:] if dot >= 0 else ""
