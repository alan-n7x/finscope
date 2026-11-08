"""Testes do parser de PDF do Itaú (`app.parsers.itau`).

A extração continua baseada em `page.extract_text()`; aqui `pdfplumber.open`
é substituído por uma página falsa para rodar sem PDF no CI.
"""

from pathlib import Path

import pytest

from app import import_engine
from app.parsers import itau
from app.parsers import parse_statement
from app.parsers.base import UnsupportedFileFormatError

ITAU_TEXT = """Itaú Unibanco
Extrato de conta corrente
Saldo em conta
R$ 627,75 R$ 0,00
emitido em: 14/08/2026
14/08/2026 PIX QRS 65.034.307 14/08 -18,50
14/08/2026 PIX TRANSF ALAN DO13/10 64,00
14/08/2026 SALDO DO DIA 609,25
"""


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakePdf:
    def __init__(self, pages: list[str]) -> None:
        self.pages = [_FakePage(text) for text in pages]

    def __enter__(self) -> "_FakePdf":
        return self

    def __exit__(self, *args) -> bool:
        return False


@pytest.fixture
def fake_pdf(monkeypatch):
    def _install(*pages: str) -> None:
        monkeypatch.setattr(itau.pdfplumber, "open", lambda _: _FakePdf(list(pages)))

    return _install


def test_extrai_lancamentos_e_classifica_transferencia_propria(fake_pdf):
    fake_pdf(ITAU_TEXT)

    txs, _, account = itau.parse_pdf(b"pdf")

    assert account == "Itaú - Conta corrente"
    assert len(txs) == 2
    assert [t.date for t in txs] == ["2026-08-14", "2026-08-14"]
    assert [t.amount for t in txs] == [18.50, 64.00]
    assert txs[0].type == "Despesa"
    assert txs[0].description == "PIX QRS 65.034.307 14/08"
    assert txs[1].type == "Receita"
    assert txs[1].category == "Transferência interna"
    assert all(t.account == "Itaú - Conta corrente" for t in txs)
    assert all(t.status == "NEW" for t in txs)


def test_ids_sao_estaveis_entre_execucoes(fake_pdf):
    fake_pdf(ITAU_TEXT)
    txs, _, _ = itau.parse_pdf(b"pdf")
    txs_again, _, _ = itau.parse_pdf(b"pdf")

    assert [t.id for t in txs] == [t.id for t in txs_again]
    assert len({t.id for t in txs}) == len(txs)


def test_snapshot_do_cabecalho_substitui_saldo_do_dia(fake_pdf):
    fake_pdf(ITAU_TEXT)

    _, snapshots, _ = itau.parse_pdf(b"pdf")

    assert len(snapshots) == 1
    assert snapshots[0].date == "2026-08-14"
    assert snapshots[0].balance == pytest.approx(627.75)


def test_parse_statement_despacha_pdf_para_itau(fake_pdf, monkeypatch):
    fake_pdf(ITAU_TEXT)
    # detecção não acha marcador do Mercado Pago e cai no fallback do Itaú
    monkeypatch.setattr("app.parsers.read_pages", lambda _: [[]])

    txs, snapshots, account = parse_statement("extrato.pdf", b"pdf")

    assert account == "Itaú - Conta corrente"
    assert len(txs) == 2
    assert snapshots[0].balance == pytest.approx(627.75)


def test_import_engine_mantem_alias_do_parser_itau(fake_pdf):
    fake_pdf(ITAU_TEXT)

    txs, _, account = import_engine.parse_itau_pdf(b"pdf")

    assert account == "Itaú - Conta corrente"
    assert len(txs) == 2


def test_extensao_desconhecida_falha_antes_de_ler(fake_pdf):
    with pytest.raises(UnsupportedFileFormatError, match="Formato não suportado"):
        parse_statement("extrato.csv", b"a,b")


def test_parse_itau_pdf_real_se_disponivel():
    pdf_path = Path("/home/alan-santos/Downloads/finanças/itau_extrato_092026 (1).pdf")
    if not pdf_path.exists():
        pytest.skip("PDF real do Itaú não está disponível nesta máquina")

    txs, snaps, guess = itau.parse_pdf(pdf_path.read_bytes())
    assert guess == "Itaú - Conta corrente"
    assert len(txs) == 52
    # ids determinísticos
    txs2, _, _ = itau.parse_pdf(pdf_path.read_bytes())
    assert [t.id for t in txs] == [t.id for t in txs2]
    # self-transfer: outs Despesa, in Itaú sem recebido Receita, categoria interna
    self_txs = [t for t in txs if "ALAN DO" in t.description]
    assert self_txs
    assert all(t.category == "Transferência interna" for t in self_txs)
    by_desc = {t.description: t.type for t in self_txs}
    assert by_desc["PIX TRANSF ALAN DO13/10"] == "Receita"
    assert all(t.account == "Itaú - Conta corrente" for t in txs)
    # header snapshot preservado
    assert any(s.date == "2026-10-14" and abs(s.balance - 0.29) < 0.01 for s in snaps)
