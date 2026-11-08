# Parsers de extrato

Guia de manutenção dos parsers de arquivo usados pela importação
(`POST /api/transactions/import/upload`).

## Estrutura

```
app/
  import_rules.py        # regras de negócio (não lê arquivo)
  parsers/
    __init__.py          # parse_statement / parse_pdf: detecção e despacho
    base.py              # TextLine, read_pages, parse_brl, erros
    ofx.py               # OFX genérico
    itau.py              # PDF do Itaú (conta corrente)
    mercadopago.py       # PDF do Mercado Pago
  import_engine.py       # shim de compatibilidade (imports antigos)
```

Fluxo do upload:

```
arquivo (.ofx/.pdf)
  → app.parsers.parse_statement              # escolhe pelo tipo/extensão
  → app.parsers.parse_pdf                    # PDF: detecta o banco pelo conteúdo
  → app.parsers.<banco>.parse_pages/parse_pdf
  → app.import_rules.reconcile_transactions
  → preview (NEW/MATCHED) no frontend
```

Todo parser devolve a mesma tupla:

```python
(transactions, snapshots, account_guess)
```

| Formato | Módulo | Como é reconhecido |
| ------- | ------ | ------------------ |
| OFX | `app.parsers.ofx.parse_ofx` | extensão `.ofx` |
| PDF do Itaú | `app.parsers.itau.parse_pdf` | fallback para PDFs sem marcador de outro banco |
| PDF do Mercado Pago | `app.parsers.mercadopago` | rodapé institucional ou título + coluna `ID da operação` |

As regras de negócio (classificação de transferência própria, categoria,
id estável, conciliação e conta de destino) ficam em `app/import_rules.py`.
Um parser novo não deve reimplementar nada disso: importe de lá.

`app/import_engine.py` não tem mais lógica; ele só reexporta `import_rules` e
os parsers para manter `scratch/*.py` e imports antigos funcionando.

## Como o parser do Mercado Pago foi desenhado

O extrato tem uma linha-âncora por lançamento:

```
Data        Descrição            ID da operação  Valor        Saldo
03-11-2026  (descrição opcional) 187493064300    R$ 1.242,00  R$ 1.242,00
```

Descrições longas quebram em linhas **acima e abaixo** da âncora. Em vez de
depender da posição das colunas, o parser:

1. **Reconhece a âncora por regex** (`ANCHOR_RE`): data `DD-MM-YYYY`, id
   numérico, valor e saldo em reais. A descrição entre a data e o id é opcional,
   então linhas simples (`Rendimentos`) e compostas usam o mesmo padrão.
2. **Agrupa os fragmentos de descrição pela distância vertical** até a âncora
   mais próxima (`_attach_descriptions`). O limite é proporcional ao espaçamento
   mediano entre lançamentos, o que absorve quebras de 1 a 3 linhas sem capturar
   cabeçalho, rodapé ou o lançamento vizinho.
3. **Valida contra o cabeçalho impresso** (`_validate`): soma das entradas,
   soma das saídas, saldo final e continuidade do saldo entre lançamentos. Se
   algo não fechar, levanta `StatementFormatError` com o valor calculado e o
   valor impresso — o import para em vez de gravar dados errados.
4. **Usa o id da operação como identidade** (`stable_id("mercadopago", id)`).
   Re-upload do mesmo extrato gera o mesmo `external_id`, mesmo que descrição ou
   formatação mudem.

As partes voláteis ficam no topo de `app/parsers/mercadopago.py`:
`LAYOUT`, `BANK_MARKER`, `TABLE_MARKERS`, `ANCHOR_RE`, `TOTALS_RE`, `PERIOD_RE`
e constantes de agrupamento. Ajustar layout normalmente é editar só ali.

O parser do Itaú segue o formato histórico `DD/MM/YYYY DESCRIÇÃO VALOR` e usa
`page.extract_text()` (uma linha por lançamento). Ele foi movido de
`import_engine.py` sem refatorar a extração — o próximo passo é criar um
fixture anonimizado e migrá-lo para `read_pages`, como o Mercado Pago.

## Quando o PDF do banco mudar

1. Guarde o PDF novo em local privado (não versionar).
2. Gere um fixture anonimizado:

   ```bash
   uv run python scripts/snapshot_pdf_layout.py \
     ~/Downloads/extrato-novo.pdf \
     tests/fixtures/mercadopago/statement-AAAA-MM.json \
     --bank mercadopago --layout mercadopago-AAAA-MM
   ```

   O script substitui CPF, agência e conta; revise nomes e descrições antes de
   commitar. Para o Itaú ainda não há fixture: o teste roda com uma página falsa
   e o PDF real é opcional (`pytest -k itau` pula se o arquivo não existir).

3. Rode os testes do banco:

   ```bash
   uv run pytest -k mercadopago -vv
   uv run pytest -k itau -vv
   ```

   A mensagem de erro aponta qual total divergiu (ex.: `Saídas`), o que indica
   linha perdida, duplicada ou âncora que deixou de casar.

4. Ajuste as constantes no topo do módulo do banco. Se a mudança for estrutural
   (ex.: lançamento em duas colunas, valor fora da âncora), ajuste
   `_collect_anchors`/`_attach_descriptions` — nunca posicione colunas por
   coordenada absoluta.
5. Atualize `LAYOUT` e o campo `layout` do fixture, e troque o teste de
   `test_fixture_usa_o_layout_suportado` se necessário.
6. Rode a suíte inteira (`uv run pytest`) antes de abrir o PR.

## Adicionar um banco novo

1. Crie `app/parsers/<banco>.py` expondo `detect(pages)` e
   `parse_pages(pages)` — ou `parse_pdf(file_bytes)` quando precisar do
   binário, como o Itaú.
2. Reutilize `TextLine`, `read_pages`, `parse_brl`, `join_description` e
   `StatementFormatError` de `app/parsers/base.py`, e as regras de
   `app/import_rules.py`.
3. Registre no `parse_pdf` de `app/parsers/__init__.py` **antes** do fallback do
   Itaú e inclua o nome em `SUPPORTED_FORMATS`.
4. Crie fixture com `scripts/snapshot_pdf_layout.py` e testes no modelo de
   `tests/test_mercadopago_parser.py` (extração, descrição quebrada, ids
   estáveis, snapshot, validação e detecção).
5. Atualize este documento e o README.

## Regras de ouro

- **Nunca confie no layout sem validar.** Compare com totais/rodapé do próprio
  PDF; falhar no preview é melhor que importar errado.
- **Identidade estável primeiro.** Use id do banco (FITID no OFX, id da operação
  no Mercado Pago); hash de campos é o último recurso.
- **Sem posição absoluta de coluna.** Derive do conteúdo ou de âncoras.
- **Fixture anonimizado e versionado.** É ele que transforma “o PDF mudou” em um
  teste que falha com diff legível.
- **Parser novo = módulo novo.** Não volte a concentrar formatos em
  `import_engine.py`: o registro existe para isolar mudanças por banco.

## Limitações conhecidas

- O parser do Itaú ainda usa `page.extract_text()` e é o fallback do registro;
  ele abre o PDF uma segunda vez (o Mercado Pago aproveita a extração já feita).
- O upload responde `400` para extensão não suportada e `422` para PDF não
  reconhecido ou layout que não fecha com os totais do extrato.
- A confirmação da importação grava `payment_method="Pix"` para todos os itens,
  igual ao comportamento anterior de Itaú/OFX.
- O frontend ainda mostra uma mensagem genérica no upload; o detalhe do
  `StatementFormatError` chega no `422`, mas não é exibido (Issue #13).
- O snapshot usa o `Saldo final` na data de encerramento do período; o
  `Saldo inicial` do cabeçalho não é gravado.
