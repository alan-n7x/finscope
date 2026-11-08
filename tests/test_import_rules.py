"""Testes das regras de negócio da importação (`app.import_rules`)."""

from app import import_rules
from app.schemas import ImportTransaction


def test_is_self_transfer():
    assert import_rules.is_self_transfer("PIX TRANSF ALAN DO14/10") is True
    assert import_rules.is_self_transfer('Pix recebido: "Cp :60701190-ALAN DOS SANTOS OLIVEIRA"') is True
    assert import_rules.is_self_transfer("PIX QRS 99 FOOD") is False
    assert import_rules.is_self_transfer("") is False


def test_stable_id_deterministico():
    a = import_rules.stable_id("itau", "2026-10-14", "53.00", "Transferência", "PIX TRANSF ALAN DO14/10")
    b = import_rules.stable_id("itau", "2026-10-14", "53.00", "Transferência", "PIX TRANSF ALAN DO14/10")
    c = import_rules.stable_id("itau", "2026-10-14", "53.01", "Transferência", "PIX TRANSF ALAN DO14/10")
    assert a == b
    assert a != c


def test_classify_transfer_type_preserva_dashboard():
    # out sempre Despesa (visível no gasto do mês)
    assert import_rules.classify_transfer_type("PIX TRANSF ALAN DO14/10", -53.0) == "Despesa"
    assert import_rules.classify_transfer_type('Pix enviado: "Cp :60701190-Alan dos Santos Oliveira"', -64.0) == "Despesa"
    # in com recebido -> Transferência (dashboard soma + pelo sniffing existente)
    assert import_rules.classify_transfer_type('Pix recebido: "Cp :60701190-ALAN DOS SANTOS OLIVEIRA"', 53.0) == "Transferência"
    # in sem recebido (Itaú) -> Receita para não inverter o sinal no dashboard
    assert import_rules.classify_transfer_type("PIX TRANSF ALAN DO13/10", 64.0) == "Receita"
    # não-self mantém regra natural
    assert import_rules.classify_transfer_type("PIX QRS 99 FOOD", -29.4) == "Despesa"
    assert import_rules.classify_transfer_type("REMUNERACAO/SALARIO", 2306.85) == "Receita"


def test_suggest_category():
    assert import_rules.suggest_category("PIX TRANSF ALAN DO14/10", True) == "Transferência interna"
    assert import_rules.suggest_category("Estorno Uber", False) == "Estorno / Reembolso"
    assert import_rules.suggest_category("Padaria", False) == "Outros"


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
    out = import_rules.reconcile_transactions([t.model_copy() for t in imp], db_outra_conta)
    assert out[0].status == "NEW"
    db_mesma_conta = [
        {"date": "2026-10-08", "amount": 262.85, "type": "Despesa",
         "description": "PIX TRANSF ALAN DO08/10", "account": "Itaú - Conta corrente"},
    ]
    out2 = import_rules.reconcile_transactions([t.model_copy() for t in imp], db_mesma_conta)
    assert out2[0].status == "MATCHED"


def test_resolve_import_account_multibanco():
    txs = [
        ImportTransaction(id="x", date="2026-10-14", type="Despesa",
                          description="a", amount=1.0, status="NEW",
                          account="Banco Inter - Conta corrente"),
    ]
    assert import_rules.resolve_import_account(None, txs) == "Banco Inter - Conta corrente"
    assert import_rules.resolve_import_account("Itaú - Conta corrente", txs) == "Itaú - Conta corrente"
    assert import_rules.resolve_import_account(None, []) == "Itaú - Conta corrente"
