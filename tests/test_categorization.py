"""Testes das regras conservadoras de categorização (`app.categorization`)."""

import pytest

from app.categorization import (
    FALLBACK_CATEGORY,
    KNOWN_CATEGORIES,
    categorize,
    normalize,
)
from app import import_rules


def test_taxonomia_tem_exatamente_as_dez_categorias_do_banco():
    assert len(KNOWN_CATEGORIES) == 10
    assert set(KNOWN_CATEGORIES) == {
        "Alimentação",
        "Assinaturas",
        "Carro",
        "Dívidas",
        "Estorno / Reembolso",
        "Outros",
        "Salário",
        "Telefone",
        "Transferência interna",
        "Transporte",
    }


def test_normalize_remove_acentos_pontuacao_e_caixa():
    assert normalize("  AÇOUGUE São José  ") == "ACOUGUE SAO JOSE"
    assert normalize("Pix enviado: \"Cp :60701190-Alan\"") == "PIX ENVIADO CP 60701190 ALAN"
    assert normalize("") == ""


def test_movimentacao_propria_tem_precedencia():
    assert (
        categorize("PIX TRANSF ALAN DO14/10", is_self=True)
        == "Transferência interna"
    )


def test_estorno_tem_precedencia_sobre_marca():
    assert categorize("Estorno Uber", is_self=False) == "Estorno / Reembolso"
    assert categorize("Reembolso Netflix", is_self=False) == "Estorno / Reembolso"


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Pagamento Totalpass", "Assinaturas"),
        ("NETFLIX.COM", "Assinaturas"),
        ("Spotify Premium", "Assinaturas"),
        ("Uber Trip", "Transporte"),
        ("99 APP", "Transporte"),
        ("Pedido 99 Food", "Alimentação"),
        ("PIX QRS 99 FOOD12/09", "Alimentação"),
        ("IFOOD *RESTAURANTE", "Alimentação"),
        ("Padaria São José", "Alimentação"),
        ("SUPERMERCADO EXTRA", "Alimentação"),
        ("AÇOUGUE DO ZE", "Alimentação"),
        ("VIVO SP", "Telefone"),
        ("BANDA LARGA CLARO", "Telefone"),
        ("PIX QRS WEBTELECOM13/09", "Telefone"),
        ("IPVA 2026", "Carro"),
        ("Pix enviado AUTOPASS SA", "Transporte"),
        ("SEGURO AUTO PORTO", "Carro"),
        ("CRED CONSIGNAD", "Dívidas"),
        ("RENEGOCIACAO ITAU", "Dívidas"),
        ("EMPRESTIMO PESSOAL", "Dívidas"),
    ],
)
def test_regras_conservadoras_de_despesa(description: str, expected: str):
    assert categorize(description) == expected


@pytest.mark.parametrize(
    "description",
    [
        "Pagamento de conta BANCO PAN S/A",
        "Pix enviado Ricardo Pereira da Silva",
        "Pagamento com Pix BUS PAY S.A",
        "Pix QRS CREDITSEC03/11",
        "Pix enviado: Rogeris Nascimento Sobrinho (Mercado Livre)",
        "Compra no Mercado Livre",
        "Parcela do celular",
        "Pagamento de boleto",
        "TIMEOUT NA CONEXAO",
        "Rendimentos",
        "",
    ],
)
def test_descricoes_ambiguas_continuam_em_outros(description: str):
    assert categorize(description) == FALLBACK_CATEGORY


def test_salario_so_para_receita():
    assert categorize("REMUNERACAO/SALARIO", amount=2306.85, tx_type="Receita") == "Salário"
    assert categorize("SALARIO", amount=5000.0) == "Salário"
    assert categorize("REMUNERACAO/SALARIO", amount=-100.0, tx_type="Despesa") == "Outros"
    assert categorize("Transferencia recebida", amount=1000.0, tx_type="Receita") == "Outros"


def test_suggest_category_delega_para_as_regras():
    assert import_rules.suggest_category("PIX TRANSF ALAN DO14/10", True) == "Transferência interna"
    assert import_rules.suggest_category("Estorno Uber", False) == "Estorno / Reembolso"
    assert import_rules.suggest_category("Padaria", False) == "Alimentação"
    assert (
        import_rules.suggest_category(
            "REMUNERACAO/SALARIO", False, amount=2306.85, tx_type="Receita"
        )
        == "Salário"
    )
    assert import_rules.suggest_category("Pix enviado Ricardo", False) == "Outros"
