"""Testes do parser OFX (`app.parsers.ofx`)."""

from app.parsers.ofx import parse_ofx


OFX_SAMPLE = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<CURDEF>BRL</CURDEF>
<BANKACCTFROM>
<BANKID>077</BANKID>
<ACCTID>72498390</ACCTID>
<ACCTTYPE>CHECKING</ACCTTYPE>
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20261001</DTSTART>
<DTEND>20261014</DTEND>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20261014</DTPOSTED>
<TRNAMT>53.00</TRNAMT>
<FITID>202610140772</FITID>
<MEMO>Pix recebido: "Cp :60701190-ALAN DOS SANTOS OLIVEIRA"</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>PAYMENT</TRNTYPE>
<DTPOSTED>20261010</DTPOSTED>
<TRNAMT>-35.91</TRNAMT>
<FITID>202610100772</FITID>
<MEMO>Pix enviado: "Cp :30306294-99 FOOD"</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20261009</DTPOSTED>
<TRNAMT>44.19</TRNAMT>
<FITID>202610090774</FITID>
<MEMO>Estorno: "Estorno no estabelecimento Uber"</MEMO>
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>32.38</BALAMT>
<DTASOF>20261014</DTASOF>
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""


def test_parse_ofx_ids_estaveis_conta_e_snapshot():
    txs, snaps, guess = parse_ofx(OFX_SAMPLE.encode())
    assert guess == "Banco Inter - Conta corrente"
    assert len(txs) == 3
    # FITID preservado -> re-upload gera o mesmo external_id
    ids = [t.id for t in txs]
    assert "ofx-202610140772" in ids
    txs2, _, _ = parse_ofx(OFX_SAMPLE.encode())
    assert [t.id for t in txs2] == ids
    # conta propagada para o confirm não cair no fallback Itaú
    assert all(t.account == "Banco Inter - Conta corrente" for t in txs)
    # self-transfer vira Transferência com categoria própria
    self_tx = next(t for t in txs if "ALAN DOS SANTOS" in t.description)
    assert self_tx.type == "Transferência"
    assert self_tx.category == "Transferência interna"
    # estorno categorizado sem poluir "Outros"
    est = next(t for t in txs if "Estorno" in t.description)
    assert est.category == "Estorno / Reembolso"
    # ledger vira snapshot (antes era lista vazia)
    assert len(snaps) == 1
    assert snaps[0].date == "2026-10-14"
    assert abs(snaps[0].balance - 32.38) < 0.01
