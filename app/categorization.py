"""Categorização conservadora de lançamentos por descrição.

Este módulo concentra as regras de descrição -> categoria usadas pela
importação (OFX, Itaú e Mercado Pago) e pelo backfill de lançamentos antigos.
Ele não lê arquivos nem toca no banco: recebe a descrição e devolve uma das
categorias canônicas já existentes no Finscope.

Política: **conservador por padrão**. Só mapeamos marcas/termos que não deixam
dúvida; qualquer coisa ambígua continua em ``Outros`` e pode ser corrigida
manualmente. Isso evita falso positivo em descrições genéricas de Pix, como
"Pagamento de conta BANCO PAN S/A" ou "Pix enviado Ricardo".

Ordem de precedência:

1. transferência entre contas próprias;
2. estorno/reembolso;
3. receita com descrição de salário;
4. regras de despesa (dívidas, carro, telefone, assinaturas, alimentação,
   transporte);
5. ``Outros``.

Para adicionar um termo, edite apenas a tupla da categoria correspondente e
inclua um caso em ``tests/test_categorization.py``. Guia em
``docs/CATEGORIZATION.md``.
"""
from __future__ import annotations

import re
import unicodedata

SELF_TRANSFER_CATEGORY = "Transferência interna"
ESTORNO_CATEGORY = "Estorno / Reembolso"
INCOME_CATEGORY = "Salário"
FALLBACK_CATEGORY = "Outros"

# Mantém exatamente a taxonomia existente no banco (10 categorias).
KNOWN_CATEGORIES = (
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
)


def _patterns(*raw: str) -> tuple[re.Pattern[str], ...]:
    """Compila os padrões de uma categoria (texto já normalizado)."""
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in raw)


# Regras aplicadas antes de separar receita/despesa.
_NEUTRAL_RULES: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = (
    (
        ESTORNO_CATEGORY,
        _patterns(r"\bESTORNO\b", r"\bREEMBOLSO\b"),
    ),
)

# Regras de receita. Só salário; outras entradas continuam em "Outros".
_INCOME_RULES: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = (
    (
        INCOME_CATEGORY,
        _patterns(
            r"\bSALARIO\b",
            r"\bREMUNERACAO\b",
            r"\bPROVENTO\b",
            r"\bFOLHA\s+DE\s+PAGAMENTO\b",
            r"\b13\s*SALARIO\b",
            r"\bDECIMO\s+TERCEIRO\b",
        ),
    ),
)

# Regras de despesa, da mais específica para a mais genérica. Termos genéricos
# como "MERCADO", "PARCELA" e "PAGAMENTO" ficam de fora de propósito.
_EXPENSE_RULES: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = (
    (
        "Dívidas",
        _patterns(
            r"\bEMPRESTIMO\b",
            r"\bCONSIGNAD\w*",
            r"\bRENEGOCIACAO\b",
            r"\bFINANCIAMENTO\b",
        ),
    ),
    (
        "Carro",
        _patterns(
            r"\bIPVA\b",
            r"\bLICENCIAMENTO\b",
            r"\bSEGURO\s+AUTO\b",
            r"\bMULTA\b",
            r"\bREVISAO\b",
            r"\bOFICINA\b",
            r"\bPNEU\b",
        ),
    ),
    (
        "Telefone",
        _patterns(
            r"\bVIVO\b",
            r"\bCLARO\b",
            r"\bTIM\b",
            r"\bALGAR\b",
            r"\bTELEFONE\b",
            r"\bBANDA\s+LARGA\b",
            r"\bWEBTELECOM\w*",
        ),
    ),
    (
        "Assinaturas",
        _patterns(
            r"\bNETFLIX\b",
            r"\bSPOTIFY\b",
            r"\bAMAZON\s+PRIME\b",
            r"\bDISNEY\b",
            r"\bHBO\b",
            r"\bICLOUD\b",
            r"\bYOUTUBE\b",
            r"\bTOTALPASS\b",
            r"\bAPPLE\s+COM\b",
        ),
    ),
    (
        "Alimentação",
        _patterns(
            r"\bIFOOD\b",
            r"\bRESTAURANTE\b",
            r"\bLANCHONETE\b",
            r"\bPADARIA\b",
            r"\bSUPERMERCADO\b",
            r"\bHIPERMERCADO\b",
            r"\bMERCEARIA\b",
            r"\bACOUGUE\b",
            r"\bPIZZARIA\b",
            r"\bCAFETERIA\b",
            r"\b99\s*FOOD\w*",
            r"\bMCDONALD\w*",
            r"\bBURGER\s*KING\b",
            r"\bSUBWAY\b",
        ),
    ),
    (
        "Transporte",
        _patterns(
            r"\bUBER\b",
            r"\b99\s*(APP|TECNOLOGIA|POP)\b",
            r"\bPOSTO\b",
            r"\bCOMBUSTIVEL\b",
            r"\bSEM\s+PARAR\b",
            r"\bESTACIONAMENTO\b",
            r"\bPEDAGIO\b",
            r"\bPASSAGEM\b",
            r"\bMETRO\b",
            r"\bONIBUS\b",
            r"\bTAXI\b",
            r"\bAUTOPASS\b",
        ),
    ),
)


def normalize(description: str) -> str:
    """Normaliza a descrição para comparação estável entre bancos.

    Remove acentos, troca pontuação por espaço, colapsa espaços e converte
    para maiúsculas. Assim "AÇOUGUE", "Açougue" e "acougue" casam com o mesmo
    padrão, sem depender do formato de cada extrato.

    Args:
        description: Descrição do lançamento como veio do extrato.

    Returns:
        Texto em ASCII maiúsculo, com tokens separados por um espaço.
    """
    decomposed = unicodedata.normalize("NFKD", description or "")
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", without_accents)
    return " ".join(spaced.upper().split())


def categorize(
    description: str,
    *,
    is_self: bool = False,
    amount: float | None = None,
    tx_type: str | None = None,
) -> str:
    """Sugere a categoria de um lançamento a partir da descrição.

    A função é determinística e não acessa banco nem configuração externa.
    ``is_self`` deve vir de ``import_rules.is_self_transfer`` para evitar
    import circular.

    Args:
        description: Descrição do lançamento como veio do extrato.
        is_self: True quando é movimentação entre contas do próprio titular.
        amount: Valor com sinal (positivo = entrada, negativo = saída). Usado
            só para inferir receita quando ``tx_type`` não é informado.
        tx_type: Tipo no padrão do preview ("Receita", "Despesa" ou
            "Transferência"), quando já conhecido.

    Returns:
        Uma das ``KNOWN_CATEGORIES``. O padrão é ``Outros``.
    """
    if is_self:
        return SELF_TRANSFER_CATEGORY

    text = normalize(description)
    if not text:
        return FALLBACK_CATEGORY

    matched = _first_match(text, _NEUTRAL_RULES)
    if matched is not None:
        return matched

    income = tx_type == "Receita" or (
        tx_type is None and amount is not None and amount > 0
    )
    if income:
        return _first_match(text, _INCOME_RULES) or FALLBACK_CATEGORY

    if tx_type == "Transferência":
        return FALLBACK_CATEGORY

    return _first_match(text, _EXPENSE_RULES) or FALLBACK_CATEGORY


def _first_match(
    text: str,
    rules: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...],
) -> str | None:
    """Retorna a categoria da primeira regra que casar com o texto."""
    for category, patterns in rules:
        if any(pattern.search(text) for pattern in patterns):
            return category
    return None
