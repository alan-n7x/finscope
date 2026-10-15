from pathlib import Path

from app import import_engine
from app.schemas import ImportTransaction


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


def test_is_self_transfer():
    assert import_engine.is_self_transfer("PIX TRANSF ALAN DO14/10") is True
    assert import_engine.is_self_transfer('Pix recebido: "Cp :60701190-ALAN DOS SANTOS OLIVEIRA"') is True
    assert import_engine.is_self_transfer("PIX QRS 99 FOOD") is False
    assert import_engine.is_self_transfer("") is False


def test_stable_id_deterministico():
    a = import_engine.stable_id("itau", "2026-10-14", "53.00", "Transferência", "PIX TRANSF ALAN DO14/10")
    b = import_engine.stable_id("itau", "2026-10-14", "53.00", "Transferência", "PIX TRANSF ALAN DO14/10")
    c = import_engine.stable_id("itau", "2026-10-14", "53.01", "Transferência", "PIX TRANSF ALAN DO14/10")
    assert a == b
    assert a != c


def test_parse_ofx_ids_estaveis_conta_e_snapshot():
    txs, snaps, guess = import_engine.parse_ofx(OFX_SAMPLE.encode())
    assert guess == "Banco Inter - Conta corrente"
    assert len(txs) == 3
    # FITID preservado -> re-upload gera o mesmo external_id
    ids = [t.id for t in txs]
    assert "ofx-202610140772" in ids
    txs2, _, _ = import_engine.parse_ofx(OFX_SAMPLE.encode())
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


def test_classify_transfer_type_preserva_dashboard():
    # out sempre Despesa (visível no gasto do mês)
    assert import_engine.classify_transfer_type("PIX TRANSF ALAN DO14/10", -53.0) == "Despesa"
    assert import_engine.classify_transfer_type('Pix enviado: "Cp :60701190-Alan dos Santos Oliveira"', -64.0) == "Despesa"
    # in com recebido -> Transferência (dashboard soma + pelo sniffing existente)
    assert import_engine.classify_transfer_type('Pix recebido: "Cp :60701190-ALAN DOS SANTOS OLIVEIRA"', 53.0) == "Transferência"
    # in sem recebido (Itaú) -> Receita para não inverter o sinal no dashboard
    assert import_engine.classify_transfer_type("PIX TRANSF ALAN DO13/10", 64.0) == "Receita"
    # não-self mantém regra natural
    assert import_engine.classify_transfer_type("PIX QRS 99 FOOD", -29.4) == "Despesa"
    assert import_engine.classify_transfer_type("REMUNERACAO/SALARIO", 2306.85) == "Receita"


def test_reconcile_exige_mesma_conta_para_transfer_interna():
    imp = [
        ImportTransaction(id="a", date="2026-10-08", type="Despesa",
                          description="PIX TRANSF ALAN DO08/10", amount=262.85,
                          status="NEW", account="Itaú - Conta corrente"),
    ]
    db_outra_conta = [
        {"date": "2026-10-08", "amount": 262.85, "type": "Despesa",
         "description": "outra", "account": "Banco Inter - Conta corrente"},
    ]
    out = import_engine.reconcile_transactions([t.model_copy() for t in imp], db_outra_conta)
    assert out[0].status == "NEW"
    db_mesma_conta = [
        {"date": "2026-10-08", "amount": 262.85, "type": "Despesa",
         "description": "PIX TRANSF ALAN DO08/10", "account": "Itaú - Conta corrente"},
    ]
    out2 = import_engine.reconcile_transactions([t.model_copy() for t in imp], db_mesma_conta)
    assert out2[0].status == "MATCHED"


def test_resolve_import_account_multibanco():
    txs = [
        ImportTransaction(id="x", date="2026-10-14", type="Despesa",
                          description="a", amount=1.0, status="NEW",
                          account="Banco Inter - Conta corrente"),
    ]
    assert import_engine.resolve_import_account(None, txs) == "Banco Inter - Conta corrente"
    assert import_engine.resolve_import_account("Itaú - Conta corrente", txs) == "Itaú - Conta corrente"
    assert import_engine.resolve_import_account(None, []) == "Itaú - Conta corrente"


def test_parse_itau_pdf_real_se_disponivel():
    pdf_path = Path("/home/alan-santos/Downloads/finanças/itau_extrato_092026 (1).pdf")
    if not pdf_path.exists():
        return
    txs, snaps, guess = import_engine.parse_itau_pdf(pdf_path.read_bytes())
    assert guess == "Itaú - Conta corrente"
    assert len(txs) == 52
    # ids determinísticos
    txs2, _, _ = import_engine.parse_itau_pdf(pdf_path.read_bytes())
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
