# Categorização de lançamentos

Regras que transformam a descrição do extrato em uma das 10 categorias do
Finscope. Ficam em `app/categorization.py` e são usadas por:

- importação OFX/Itaú/Mercado Pago (`app.import_rules.suggest_category`);
- backfill de lançamentos antigos (`scripts/recategorize_transactions.py`).

A mesma regra vale para todos os bancos: um parser novo não deve implementar
categorização própria.

## Política: conservador por padrão

Só mapeamos marcas/termos que não deixam dúvida. Descrições genéricas de Pix,
pagamento de boleto e transferência para pessoa física continuam em `Outros`.
O objetivo é não inventar categoria; o usuário pode corrigir manualmente.

## Precedência

1. **Transferência interna** (`ALAN DO...` em `is_self_transfer`);
2. **Estorno / Reembolso** (`ESTORNO`, `REEMBOLSO`);
3. **Salário**, apenas para receita (`SALARIO`, `REMUNERACAO`, `PROVENTO`,
   `FOLHA DE PAGAMENTO`, `13 SALARIO`, `DECIMO TERCEIRO`);
4. regras de despesa;
5. `Outros`.

## Regras de despesa

| Categoria | Termos reconhecidos (texto normalizado) |
| --- | --- |
| Dívidas | `EMPRESTIMO`, `CONSIGNAD*`, `RENEGOCIACAO`, `FINANCIAMENTO` |
| Carro | `IPVA`, `LICENCIAMENTO`, `SEGURO AUTO`, `MULTA`, `REVISAO`, `OFICINA`, `PNEU` |
| Telefone | `VIVO`, `CLARO`, `TIM`, `ALGAR`, `TELEFONE`, `BANDA LARGA`, `WEBTELECOM*` |
| Assinaturas | `NETFLIX`, `SPOTIFY`, `AMAZON PRIME`, `DISNEY`, `HBO`, `ICLOUD`, `YOUTUBE`, `TOTALPASS`, `APPLE COM` |
| Alimentação | `IFOOD`, `RESTAURANTE`, `LANCHONETE`, `PADARIA`, `SUPERMERCADO`, `HIPERMERCADO`, `MERCEARIA`, `ACOUGUE`, `PIZZARIA`, `CAFETERIA`, `99 FOOD*`, `MCDONALD*`, `BURGER KING`, `SUBWAY` |
| Transporte | `UBER`, `99 APP/TECNOLOGIA/POP`, `POSTO`, `COMBUSTIVEL`, `SEM PARAR`, `ESTACIONAMENTO`, `PEDAGIO`, `PASSAGEM`, `METRO`, `ONIBUS`, `TAXI`, `AUTOPASS` |

A normalização remove acentos, troca pontuação por espaço, colapsa espaços e
converte para maiúsculas. Por isso `AÇOUGUE`, `Açougue` e `acougue` casam com o
mesmo padrão, e `99 FOOD12/09` casa com `99 FOOD*`.

Termos deliberadamente **fora** das regras: `MERCADO` (confunde com Mercado
Pago/Livre), `PARCELA` (pode ser qualquer compra), `PAGAMENTO` e `PIX` (genéricos
demais).

## Adicionar um termo

1. Edite a tupla da categoria em `app/categorization.py`
   (`_EXPENSE_RULES`, `_INCOME_RULES` ou `_NEUTRAL_RULES`).
2. Prefira regex ancorado em palavra: `r"\bTERMO\b"`. Para marcas que aparecem
   coladas a datas/números no extrato, use prefixo: `r"\bTERMO\w*"`.
3. Inclua um caso em `tests/test_categorization.py` (tanto positivo quanto um
   ambíguo que deve continuar em `Outros`).
4. Rode `pytest -k categorization` e depois o backfill em dry-run.

## Backfill de lançamentos antigos

Lançamentos já gravados como `Outros` não mudam sozinhos. O script reaplica as
regras apenas no que foi importado e nunca sobrescreve categoria editada
manualmente:

- alvo: `external_id LIKE 'import:%'` **e** categoria atual `Outros`;
- `--month YYYY-MM` limita o período;
- sem `--apply` é **dry-run**;
- imprime amostra e resumo por categoria;
- reutiliza `categorize()`, não SQL hardcoded.

```bash
# Conferir
uv run python scripts/recategorize_transactions.py --month 2026-11

# Aplicar
uv run python scripts/recategorize_transactions.py --month 2026-11 --apply
```

No container:

```bash
docker compose exec backend uv run python scripts/recategorize_transactions.py --apply
```

O script é idempotente: depois de aplicar, uma nova execução não encontra mais
`Outros` elegíveis para as mesmas regras.

## Limitações

- É heurística: regras conservadoras deixam muitos lançamentos em `Outros` de
  propósito. Categorias editadas manualmente têm prioridade e não são tocadas.
- A agregação do gráfico de Analytics ainda é feita no frontend; mover para um
  endpoint no backend é a próxima PR (Issue #16).
- O preview de importação ainda não permite trocar a categoria sugerida; isso
  também fica para a evolução da UX de importação.
