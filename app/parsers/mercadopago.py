"""Parser do extrato em PDF do Mercado Pago (conta digital).

O layout é reconhecido por uma linha-âncora por lançamento:

    03-11-2026 187493064300 R$ 1.242,00 R$ 1.242,00

`Data  Descrição opcional  ID da operação  Valor  Saldo`.
Descrições longas quebram em linhas acima e abaixo da âncora; o parser agrupa
esses fragmentos pela distância vertical até a âncora mais próxima, sem fixar
posições de coluna. Assim, variações de espaçamento, largura de página ou
quebra de linha não exigem mudança de código — só um novo regex de âncora, se o
formato do bloco mudar.

Além dos lançamentos, o cabeçalho (`Entradas`, `Saidas`, `Saldo inicial`,
`Saldo final`, `Periodo`) é lido e usado como **contrato de validação**: se a
soma do que foi extraído não fechar com o total impresso, o parser falha com
`StatementFormatError` em vez de importar dados errados.

Passo a passo de manutenção em `docs/PARSERS.md`.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from statistics import median
from typing import Sequence

from ..import_rules import (
    classify_transfer_type,
    is_self_transfer,
    stable_id,
    suggest_category,
)
from ..schemas import BalanceSnapshot, ImportTransaction
from .base import (
    ParserResult,
    StatementFormatError,
    TextLine,
    join_description,
    parse_brl,
)

BANK = "Mercado Pago"
LAYOUT = "mercadopago-2026-11"

# Marcadores de identificação. O rodapé com a razão social só aparece na última
# página, por isso a detecção também aceita o par título + coluna.
BANK_MARKER = "mercado pago instituicao de pagamento"
TABLE_MARKERS = ("detalhe dos movimentos", "id da operacao")

# Linha-âncora: data, descrição (opcional), id da operação, valor e saldo.
ANCHOR_RE = re.compile(
    r"^(?P<date>\d{2}-\d{2}-\d{4})\s+"
    r"(?P<description>.*?)"
    r"(?P<operation_id>\d{8,})\s+"
    r"R\$\s*(?P<amount>-?\d+(?:\.\d{3})*,\d{2})\s+"
    r"R\$\s*(?P<balance>-?\d+(?:\.\d{3})*,\d{2})$"
)

TOTALS_RE = {
    "income": re.compile(r"Entradas:\s*R\$\s*(?P<value>-?\d+(?:\.\d{3})*,\d{2})", re.IGNORECASE),
    "expenses": re.compile(r"Sa[ií]das:\s*R\$\s*(?P<value>-?\d+(?:\.\d{3})*,\d{2})", re.IGNORECASE),
    "initial": re.compile(r"Saldo inicial:\s*R\$\s*(?P<value>-?\d+(?:\.\d{3})*,\d{2})", re.IGNORECASE),
    "final": re.compile(r"Saldo final:\s*R\$\s*(?P<value>-?\d+(?:\.\d{3})*,\d{2})", re.IGNORECASE),
}
PERIOD_RE = re.compile(
    r"Per[ií]odo:\s*De\s*(?P<start>\d{2}-\d{2}-\d{4})\s*(?:a[l]?|ao)\s*"
    r"(?P<end>\d{2}-\d{2}-\d{4})",
    re.IGNORECASE,
)

# Distância máxima de um fragmento de descrição até a âncora, como fração do
# espaçamento mediano entre lançamentos. Absorve quebras de 1 a 3 linhas sem
# capturar cabeçalho, rodapé ou a linha do lançamento vizinho.
DESCRIPTION_SPAN_RATIO = 0.75
DEFAULT_ROW_SPACING = 35.0
VALUE_TOLERANCE = 0.01


@dataclass
class _Anchor:
    """Lançamento ainda com a descrição em pedaços."""

    page: int
    top: float
    date: str
    description: str
    operation_id: str
    amount: float
    balance: float
    fragments: list[TextLine] = field(default_factory=list)


@dataclass(frozen=True)
class _Header:
    """Totais impressos no cabeçalho, usados para validar a extração."""

    income: float
    expenses: float
    initial: float | None
    final: float
    period_end: str | None


def detect(pages: Sequence[Sequence[TextLine]]) -> bool:
    """Indica se o PDF parece ser um extrato do Mercado Pago.

    Args:
        pages: Linhas visuais extraídas por `app.parsers.base.read_pages`.

    Returns:
        True quando o rodapé institucional ou o par título/coluna do extrato
        é encontrado.
    """
    text = _normalized_text(pages)
    return BANK_MARKER in text or all(marker in text for marker in TABLE_MARKERS)


def parse_pages(pages: Sequence[Sequence[TextLine]]) -> ParserResult:
    """Converte as linhas do extrato em lançamentos e snapshot de saldo.

    Args:
        pages: Linhas visuais extraídas por `app.parsers.base.read_pages`.

    Returns:
        Tupla `(transações, snapshots, "Mercado Pago")`. O snapshot usa o
        `Saldo final` do cabeçalho na data de encerramento do período.

    Raises:
        StatementFormatError: Quando nenhuma âncora é encontrada ou quando os
            totais extraídos não fecham com o cabeçalho do PDF.
    """
    anchors = _collect_anchors(pages)
    header = _read_header(pages)
    if not anchors:
        # Extrato sem movimentação: devolve preview vazio, mas mantém o saldo.
        # Só é erro quando o cabeçalho indica movimento que não foi extraído.
        if abs(header.income) > VALUE_TOLERANCE or abs(header.expenses) > VALUE_TOLERANCE:
            raise StatementFormatError(
                f"Nenhum lançamento encontrado no extrato do Mercado Pago ({LAYOUT}), "
                "mas o cabeçalho indica movimentação. Se o PDF mudou de layout, "
                "veja docs/PARSERS.md."
            )
        snapshots = (
            [BalanceSnapshot(date=header.period_end, balance=header.final)]
            if header.period_end
            else []
        )
        return [], snapshots, BANK

    _attach_descriptions(pages, anchors)
    _validate(anchors, header)

    transactions = [_to_transaction(anchor) for anchor in anchors]
    snapshot_date = header.period_end or _iso_date(anchors[-1].date)
    snapshots = [BalanceSnapshot(date=snapshot_date, balance=header.final)]
    return transactions, snapshots, BANK


def _collect_anchors(pages: Sequence[Sequence[TextLine]]) -> list[_Anchor]:
    """Localiza as linhas-âncora de lançamento em todas as páginas."""
    anchors: list[_Anchor] = []
    for page_index, lines in enumerate(pages):
        for line in lines:
            match = ANCHOR_RE.match(line.text)
            if match is None:
                continue
            anchors.append(
                _Anchor(
                    page=page_index,
                    top=line.top,
                    date=match.group("date"),
                    description=match.group("description").strip(),
                    operation_id=match.group("operation_id"),
                    amount=parse_brl(match.group("amount")),
                    balance=parse_brl(match.group("balance")),
                )
            )
    return anchors


def _attach_descriptions(
    pages: Sequence[Sequence[TextLine]], anchors: list[_Anchor]
) -> None:
    """Agrupa as linhas de descrição em volta de cada âncora.

    A âncora fica no meio vertical do lançamento, então cada fragmento é
    atribuído à âncora mais próxima da mesma página. O limite relativo ao
    espaçamento mediano evita capturar cabeçalho, rodapé e páginas vizinhas.
    """
    limit = _median_spacing(anchors) * DESCRIPTION_SPAN_RATIO
    by_page: dict[int, list[_Anchor]] = defaultdict(list)
    for anchor in anchors:
        by_page[anchor.page].append(anchor)

    for page_index, page_anchors in by_page.items():
        for line in pages[page_index]:
            if ANCHOR_RE.match(line.text):
                continue
            nearest = min(page_anchors, key=lambda anchor: abs(anchor.top - line.top))
            if abs(nearest.top - line.top) <= limit:
                nearest.fragments.append(line)

    for anchor in anchors:
        ordered = sorted(anchor.fragments, key=lambda line: line.top)
        anchor.description = join_description(
            [anchor.description, *(line.text for line in ordered)]
        )


def _median_spacing(anchors: Sequence[_Anchor]) -> float:
    """Espaçamento vertical típico entre lançamentos consecutivos."""
    gaps = [
        current.top - previous.top
        for previous, current in zip(anchors, anchors[1:])
        if previous.page == current.page and current.top > previous.top
    ]
    return median(gaps) if gaps else DEFAULT_ROW_SPACING


def _read_header(pages: Sequence[Sequence[TextLine]]) -> _Header:
    """Lê os totais do cabeçalho usados na validação.

    Raises:
        StatementFormatError: Quando `Entradas`, `Saidas` ou `Saldo final` não
            são encontrados.
    """
    text = "\n".join(line.text for page in pages for line in page)
    values: dict[str, float] = {}
    for key, pattern in TOTALS_RE.items():
        match = pattern.search(text)
        if match is not None:
            values[key] = parse_brl(match.group("value"))

    missing = [key for key in ("income", "expenses", "final") if key not in values]
    if missing:
        raise StatementFormatError(
            f"Cabeçalho do extrato do Mercado Pago incompleto ({LAYOUT}): "
            f"não encontrei {', '.join(missing)}. Veja docs/PARSERS.md."
        )

    period = PERIOD_RE.search(text)
    return _Header(
        income=values["income"],
        expenses=values["expenses"],
        initial=values.get("initial"),
        final=values["final"],
        period_end=_iso_date(period.group("end")) if period else None,
    )


def _validate(anchors: Sequence[_Anchor], header: _Header) -> None:
    """Confere a extração contra os totais impressos no PDF.

    Valida entradas, saídas, o saldo final e a continuidade do saldo entre
    lançamentos consecutivos. Qualquer divergência significa linha perdida,
    duplicada ou layout novo — e o import é abortado em vez de gravar errado.

    Raises:
        StatementFormatError: Na primeira divergência encontrada.
    """
    credits = sum(anchor.amount for anchor in anchors if anchor.amount > 0)
    debits = sum(-anchor.amount for anchor in anchors if anchor.amount < 0)
    _ensure_close(credits, header.income, "Entradas")
    _ensure_close(debits, abs(header.expenses), "Saídas")
    _ensure_close(anchors[-1].balance, header.final, "Saldo final")

    if header.initial is not None:
        _ensure_close(anchors[0].balance, header.initial + anchors[0].amount, "primeiro saldo")

    for previous, current in zip(anchors, anchors[1:]):
        expected = previous.balance + current.amount
        _ensure_close(current.balance, expected, f"saldo após {current.date}")


def _ensure_close(computed: float, expected: float, label: str) -> None:
    """Falha quando a diferença passa da tolerância de centavos."""
    if abs(computed - expected) > VALUE_TOLERANCE:
        raise StatementFormatError(
            f"Extrato do Mercado Pago divergente em {label}: calculado "
            f"R$ {computed:.2f}, impresso no PDF R$ {expected:.2f}. "
            "O layout pode ter mudado; veja docs/PARSERS.md."
        )


def _to_transaction(anchor: _Anchor) -> ImportTransaction:
    """Converte a âncora já completa em lançamento do preview."""
    description = anchor.description.strip()
    self_transfer = is_self_transfer(description)
    t_type = classify_transfer_type(description, anchor.amount)
    return ImportTransaction(
        # O id da operação é único e imutável no Mercado Pago: re-upload do
        # mesmo extrato gera o mesmo external_id mesmo se descrição/valor
        # mudarem de formatação.
        id=stable_id("mercadopago", anchor.operation_id),
        date=_iso_date(anchor.date),
        type=t_type,
        description=description,
        amount=abs(anchor.amount),
        status="NEW",
        category=suggest_category(
            description,
            self_transfer,
            amount=anchor.amount,
            tx_type=t_type,
        ),
        account=BANK,
    )


def _iso_date(ddmmyyyy: str) -> str:
    """Converte `DD-MM-YYYY` (padrão do PDF) em `YYYY-MM-DD`."""
    day, month, year = ddmmyyyy.split("-")
    return f"{year}-{month}-{day}"


def _normalized_text(pages: Sequence[Sequence[TextLine]]) -> str:
    """Texto do PDF sem acentos e em minúsculas, para detecção tolerante."""
    text = "\n".join(line.text for page in pages for line in page).lower()
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))
