"""Gera um fixture anonimizado a partir de um PDF de extrato.

O parser é testado sobre as linhas visuais do PDF (texto + coordenada
vertical), não sobre o binário. Este script extrai essas linhas no mesmo
formato usado por `app.parsers.base.read_pages` e grava um JSON que pode ser
versionado com segurança: CPF, agência e número da conta são substituídos por
valores fictícios antes da gravação.

Uso:
    uv run python scripts/snapshot_pdf_layout.py \
        caminho/extrato.pdf tests/fixtures/mercadopago/statement_2026-11.json

Depois de gerar, rode `pytest -k mercadopago` e ajuste o parser/fixture
conforme `docs/PARSERS.md`.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from app.parsers.base import read_pages

CPF_RE = re.compile(r"(CPF/CNPJ:\s*)[\d.\-/]+", re.IGNORECASE)
AGENCY_RE = re.compile(r"(Ag[êe]ncia:\s*)\S+", re.IGNORECASE)
ACCOUNT_RE = re.compile(r"(Conta:\s*)\S+", re.IGNORECASE)

REDACTIONS = (
    (CPF_RE, r"\g<1>000.000.000-00"),
    (AGENCY_RE, r"\g<1>0"),
    (ACCOUNT_RE, r"\g<1>0"),
)


def redact(text: str) -> str:
    """Substitui dados sensíveis mantendo o tamanho do texto original.

    Args:
        text: Linha extraída do PDF.

    Returns:
        A linha com CPF, agência e conta trocados por valores fictícios.
    """
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def build_fixture(pdf_path: pathlib.Path, bank: str, layout: str, redact_pii: bool) -> dict:
    """Monta o dicionário versionável a partir do PDF.

    Args:
        pdf_path: Caminho do PDF de origem.
        bank: Nome do banco/instituição usado no fixture.
        layout: Identificador do layout suportado pelo parser.
        redact_pii: Quando True, aplica as substituições de dados sensíveis.

    Returns:
        Dicionário com `bank`, `layout` e as linhas de cada página.
    """
    pages = read_pages(pdf_path.read_bytes())
    return {
        "bank": bank,
        "layout": layout,
        "pages": [
            [
                {"top": line.top, "text": redact(line.text) if redact_pii else line.text}
                for line in page
            ]
            for page in pages
        ],
    }


def main() -> int:
    """Ponto de entrada do script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=pathlib.Path, help="PDF de extrato a fotografar")
    parser.add_argument("out", type=pathlib.Path, help="Caminho do JSON de saída")
    parser.add_argument("--bank", default="desconhecido", help="Nome do banco no fixture")
    parser.add_argument("--layout", default="desconhecido", help="Identificador do layout")
    parser.add_argument(
        "--keep-pii",
        action="store_true",
        help="Não anonimiza CPF/agência/conta (evite versionar o resultado)",
    )
    args = parser.parse_args()

    fixture = build_fixture(args.pdf, args.bank, args.layout, redact_pii=not args.keep_pii)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = sum(len(page) for page in fixture["pages"])
    print(f"Fixture gravado em {args.out} ({len(fixture['pages'])} páginas, {lines} linhas).")
    if not args.keep_pii:
        print("CPF, agência e conta foram anonimizados; revise nomes/descrições antes de commitar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
