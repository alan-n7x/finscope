"""Contrato e utilitários compartilhados pelos parsers de extrato em PDF.

Cada banco tem o seu módulo em `app/parsers/` e devolve sempre a mesma tupla:
`(lançamentos, snapshots de saldo, palpite de conta)`. O registro em
`app/parsers/__init__.py` detecta o banco pelo conteúdo do arquivo e delega ao
parser correspondente, então uma mudança de layout exige mexer apenas no módulo
daquele banco.

O fluxo de manutenção (fixtures, testes e atualização de layout) está em
`docs/PARSERS.md`.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Sequence

import pdfplumber

from ..schemas import BalanceSnapshot, ImportTransaction

ParserResult = tuple[list[ImportTransaction], list[BalanceSnapshot], str]


class StatementFormatError(ValueError):
    """Falha de layout ou de validação do extrato.

    A mensagem é escrita para chegar ao usuário final (ou ao log), explicando o
    que não fechou e apontando para `docs/PARSERS.md` quando o layout mudou.
    """


@dataclass(frozen=True)
class TextLine:
    """Linha visual do PDF, com a coordenada vertical usada para agrupar.

    Attributes:
        top: Distância do topo da página, em pontos.
        text: Texto da linha com espaços normalizados.
    """

    top: float
    text: str


def read_pages(file_bytes: bytes) -> list[list[TextLine]]:
    """Extrai as linhas visuais de cada página do PDF.

    Usa `extract_text_lines` para preservar a quebra de linha visual: no
    Mercado Pago, por exemplo, a descrição de um lançamento pode ocupar linhas
    acima e abaixo da linha que contém data, id, valor e saldo.

    Args:
        file_bytes: Conteúdo bruto do arquivo `.pdf`.

    Returns:
        Uma lista por página; cada página é uma lista de `TextLine` na ordem
        em que aparecem no documento.

    Raises:
        pdfplumber.PDFSyntaxError: Quando o arquivo não é um PDF válido.
    """
    pages: list[list[TextLine]] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            lines = [
                TextLine(top=round(line["top"], 2), text=" ".join(line["text"].split()))
                for line in page.extract_text_lines()
                if line["text"].strip()
            ]
            pages.append(lines)
    return pages


def parse_brl(raw: str) -> float:
    """Converte um valor monetário do extrato em float.

    Args:
        raw: Valor como aparece no PDF, com ou sem `R$` (ex.: `"1.242,81"`,
            `"-75,00"`).

    Returns:
        O valor numérico correspondente.
    """
    cleaned = raw.replace("R$", "").strip().replace(".", "").replace(",", ".")
    return float(cleaned)


def join_description(parts: Sequence[str]) -> str:
    """Junta fragmentos de descrição quebrados em várias linhas.

    Args:
        parts: Fragmentos na ordem visual em que aparecem no PDF.

    Returns:
        A descrição em uma única linha, com espaços normalizados.
    """
    return " ".join(part.strip() for part in parts if part.strip())
