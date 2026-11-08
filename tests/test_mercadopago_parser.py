"""Testes do parser de PDF do Mercado Pago.

O fixture é uma fotografia anonimizada das linhas visuais de um extrato real
(`tests/fixtures/mercadopago/statement_2026-11.json`). Para atualizar depois de
uma mudança de layout, veja `docs/PARSERS.md`.
"""
import copy
import json
from pathlib import Path

import pytest

from app import import_rules
from app.parsers import StatementFormatError, mercadopago, parse_pdf
from app.parsers import itau
from app.parsers.base import TextLine

FIXTURE = Path(__file__).parent / "fixtures" / "mercadopago" / "statement_2026-11.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def load_pages() -> list[list[TextLine]]:
    fixture = load_fixture()
    return [
        [TextLine(top=line["top"], text=line["text"]) for line in page]
        for page in fixture["pages"]
    ]


def pages_from(fixture: dict) -> list[list[TextLine]]:
    return [
        [TextLine(top=line["top"], text=line["text"]) for line in page]
        for page in fixture["pages"]
    ]


def test_fixture_usa_o_layout_suportado():
    assert load_fixture()["layout"] == mercadopago.LAYOUT


def test_detect_reconhece_mercadopago_pelo_conteudo():
    assert mercadopago.detect(load_pages()) is True

    itau_lines = [
        [
            TextLine(top=10.0, text="Itaú Unibanco"),
            TextLine(top=20.0, text="SALDO DO DIA 14/08/2026 18,50"),
        ]
    ]
    assert mercadopago.detect(itau_lines) is False


def test_extrai_todos_os_lancamentos_do_periodo():
    txs, _, account = mercadopago.parse_pages(load_pages())

    assert account == "Mercado Pago"
    assert len(txs) == 11
    assert [t.date for t in txs] == [
        "2026-11-03",
        "2026-11-03",
        "2026-11-03",
        "2026-11-03",
        "2026-11-03",
        "2026-11-04",
        "2026-11-04",
        "2026-11-05",
        "2026-11-05",
        "2026-11-05",
        "2026-11-05",
    ]
    assert [t.amount for t in txs] == [
        1242.00,
        75.00,
        96.04,
        100.00,
        5.00,
        0.44,
        89.90,
        0.37,
        55.00,
        30.00,
        33.00,
    ]
    assert all(t.account == "Mercado Pago" for t in txs)
    assert all(t.status == "NEW" for t in txs)


def test_reune_descricoes_quebradas_em_varias_linhas():
    txs, _, _ = mercadopago.parse_pages(load_pages())
    descriptions = [t.description for t in txs]

    # quebram em duas linhas no PDF (acima e abaixo da âncora)
    assert "Pix recebido ALAN DOS SANTOS OLIVEIRA" in descriptions
    assert "Pagamento com Pix Rogeris Nascimento Sobrinho" in descriptions
    assert "Pagamento de conta BANCO PAN S/A" in descriptions
    assert "Pix enviado Ricardo Pereira da Silva" in descriptions
    assert "Pagamento com Pix BUS PAY S.A" in descriptions
    assert "Pix enviado Alan dos Santos Oliveira" in descriptions
    assert "Pagamento com Pix Jodemir Holanda Sobrinho" in descriptions
    # já vinham inteiras na linha-âncora
    assert "Rendimentos" in descriptions
    assert "Pagamento Totalpass" in descriptions


def test_transferencia_entre_contas_proprias_segue_a_convencao_do_ledger():
    txs, _, _ = mercadopago.parse_pages(load_pages())
    by_description = {t.description: t for t in txs}

    received = by_description["Pix recebido ALAN DOS SANTOS OLIVEIRA"]
    assert received.type == "Transferência"
    assert received.category == "Transferência interna"

    sent = by_description["Pix enviado Alan dos Santos Oliveira"]
    assert sent.type == "Despesa"
    assert sent.category == "Transferência interna"


def test_ids_sao_estaveis_e_baseados_no_id_da_operacao():
    txs, _, _ = mercadopago.parse_pages(load_pages())
    txs_again, _, _ = mercadopago.parse_pages(load_pages())

    assert [t.id for t in txs] == [t.id for t in txs_again]
    assert len({t.id for t in txs}) == len(txs)
    assert txs[0].id == import_rules.stable_id("mercadopago", "187493064300")


def test_snapshot_usa_o_saldo_final_na_data_de_fechamento_do_periodo():
    _, snapshots, _ = mercadopago.parse_pages(load_pages())

    assert len(snapshots) == 1
    assert snapshots[0].date == "2026-11-05"
    assert snapshots[0].balance == pytest.approx(758.87)


def test_validacao_aborta_quando_um_lancamento_some():
    fixture = load_fixture()
    pages = pages_from(fixture)
    # remove a âncora do último lançamento (data 05-11, R$ -33,00)
    pages[1] = [line for line in pages[1] if "186928056793" not in line.text]

    with pytest.raises(StatementFormatError, match="Saídas"):
        mercadopago.parse_pages(pages)


def test_validacao_aborta_quando_o_total_do_cabecalho_muda():
    fixture = copy.deepcopy(load_fixture())
    fixture["pages"][0] = [
        {**line, "text": line["text"].replace("1.242,81", "1.142,81")}
        for line in fixture["pages"][0]
    ]

    with pytest.raises(StatementFormatError, match="Entradas"):
        mercadopago.parse_pages(pages_from(fixture))


def test_extrato_sem_movimentacao_devolve_preview_vazio_com_saldo():
    pages = [[
        TextLine(top=10.0, text="EXTRATO DE CONTA"),
        TextLine(top=20.0, text="Periodo: De 01-11-2026 al 30-11-2026"),
        TextLine(top=30.0, text="Entradas: R$ 0,00"),
        TextLine(top=40.0, text="Saldo inicial: R$ 0,00 Saldo final: R$ 12,34"),
        TextLine(top=50.0, text="Saidas: R$ 0,00"),
        TextLine(top=60.0, text="DETALHE DOS MOVIMENTOS"),
        TextLine(top=70.0, text="Data Descrição ID da operação Valor Saldo"),
    ]]

    txs, snapshots, account = mercadopago.parse_pages(pages)

    assert (txs, account) == ([], "Mercado Pago")
    assert len(snapshots) == 1
    assert snapshots[0].date == "2026-11-30"
    assert snapshots[0].balance == pytest.approx(12.34)


def test_cabecalho_com_movimentacao_e_sem_ancora_falha():
    pages = [[
        TextLine(top=10.0, text="Periodo: De 01-11-2026 al 30-11-2026"),
        TextLine(top=20.0, text="Entradas: R$ 10,00"),
        TextLine(top=30.0, text="Saldo inicial: R$ 0,00 Saldo final: R$ 10,00"),
        TextLine(top=40.0, text="Saidas: R$ 0,00"),
    ]]

    with pytest.raises(StatementFormatError, match="layout"):
        mercadopago.parse_pages(pages)


def test_parse_pdf_delega_para_o_parser_do_banco(monkeypatch):
    monkeypatch.setattr("app.parsers.read_pages", lambda _: load_pages())
    monkeypatch.setattr(
        itau,
        "parse_pdf",
        lambda _: pytest.fail("não deveria chamar o parser do Itaú"),
    )

    txs, snapshots, account = parse_pdf(b"pdf")
    assert account == "Mercado Pago"
    assert len(txs) == 11
    assert snapshots[0].balance == pytest.approx(758.87)


def test_parse_pdf_invalido_falha_com_mensagem_acionavel():
    with pytest.raises(StatementFormatError, match="PDF"):
        parse_pdf(b"isto nao e um pdf")


def test_parse_pdf_desconhecido_falha_com_mensagem_acionavel(monkeypatch):
    itau_pages = [[TextLine(top=10.0, text="EXTRATO DE CONTA")]]
    monkeypatch.setattr("app.parsers.read_pages", lambda _: itau_pages)
    monkeypatch.setattr(
        itau,
        "parse_pdf",
        lambda _: ([], [], "Itaú - Conta corrente"),
    )

    with pytest.raises(StatementFormatError, match="docs/PARSERS.md"):
        parse_pdf(b"pdf")
