# Fluxos de inserção e atualização

## Regra geral

Toda entrada deve responder:

- O que aconteceu?
- Quando?
- Qual o valor?
- Em qual conta?
- É realizado ou previsto?
- Tem relação com dívida, parcela ou recorrência?

## Despesa comum

Mensagem:

> Gastei R$ 35 no iFood pelo Pix do Itaú.

Operação:

1. Criar `Lancamento` do tipo `Despesa`.
2. Definir conta, categoria, descrição e forma de pagamento.
3. Marcar como pago se já ocorreu.
4. Atualizar projeção e orçamento.

## Receita

Mensagem:

> Recebi R$ 2.500 de salário no Itaú.

Operação:

1. Criar `Lancamento` do tipo `Receita`.
2. Se corresponder a uma recorrência prevista, vincular pelo ID.
3. Substituir o previsto pelo realizado; nunca contar os dois.

## Transferência entre contas próprias

Mensagem:

> Transferi R$ 200 do Santander para o Itaú.

Operação:

1. Informar conta de origem.
2. Informar conta de destino.
3. Atualizar ambos os saldos.
4. Manter impacto financeiro consolidado igual a zero.

## Compra parcelada

Mensagem:

> Comprei peças por R$ 700 em cinco parcelas no Santander. Primeira em 12/08.

Criar somente um plano:

```json
{
  "description": "Peças do carro",
  "category": "Carro",
  "total_amount": 700.00,
  "installment_count": 5,
  "installment_amount": 140.00,
  "first_due_date": "2026-08-12",
  "account": "Cartão Santander"
}
```

O sistema deriva os vencimentos. Para fluxo de caixa, considerar as parcelas, não o total e as parcelas simultaneamente.

## Pagamento de parcela

Mensagem:

> Paguei a parcela de R$ 140 das peças.

Operação atômica:

1. Criar lançamento realizado.
2. Vincular ao plano e à parcela.
3. Marcar parcela como paga.
4. Atualizar quantidade paga e saldo restante.
5. Recalcular a projeção.

Se uma das etapas falhar, nenhuma deve ser gravada.

## Dívida sem acordo

Mensagem:

> Descobri uma multa de R$ 300 e ainda não sei quando vou pagar.

Operação:

1. Criar dívida ativa.
2. Não criar pagamento futuro sem data.
3. Incluir no endividamento e patrimônio líquido.
4. Exibir alerta de compromisso sem plano.

## Pagamento único planejado

Se houver data pretendida, criar evento avulso ligado à dívida. Quando pago, transformar em lançamento realizado e atualizar o saldo da dívida.

## Proposta de negociação

Enquanto não aceita:

- registrar em `Propostas`;
- excluir dos totais financeiros;
- usar somente para comparação.

Enquanto a proposta estiver pendente, o sistema pode exibi-la em indicadores de cenário:

- `divida_reconhecida`: obrigações ativas e parcelamentos já reconhecidos;
- `divida_ampliada_original`: dívida reconhecida mais os saldos originais das ofertas pendentes;
- `quitacao_com_descontos`: dívida ampliada menos a economia máxima informada.

Esses indicadores são analíticos. Não criam lançamento, parcela ou impacto no fluxo de caixa.

Quando aceita:

1. Marcar proposta como aceita.
2. Marcar dívida original como renegociada.
3. Criar acordo.
4. Criar entrada e parcelas do acordo.
5. Impedir dupla contagem.

Depois da aceitação, retirar a proposta dos indicadores pendentes e incluir somente o novo acordo nos compromissos reconhecidos.

## Receita ou despesa recorrente

Cadastrar uma regra:

```json
{
  "id": "SALARIO",
  "type": "income",
  "amount": 2336.09,
  "start_date": "2026-08-01",
  "end_date": "2026-12-31",
  "day": 1,
  "active": true
}
```

Quando o evento ocorrer, o lançamento realizado deve substituir a ocorrência prevista.

### Confiança e resultado da receita

Toda receita prevista deve possuir nível de confiança:

- `Alta`: valor e data confirmados;
- `Média`: valor observado ou recorrente, sujeito a pequena variação;
- `Baixa`: valor estimado ou dependente de confirmação.

Os indicadores de receita devem manter separadas as entradas de baixa confiança. A receita total estimada não deve ser apresentada como dinheiro livre; o sistema deve descontar parcelas, despesas, eventos avulsos e orçamento reservado para calcular o resultado líquido.

## Benefício restrito recorrente

Mensagem:

> Recebo R$ 849 de vale-alimentação por mês.

Criar uma regra recorrente separada:

```json
{
  "id": "VA-2026",
  "type": "restricted_benefit",
  "category": "Alimentação",
  "amount": 849.00,
  "start_date": "2026-08-01",
  "end_date": "2026-12-31",
  "day": null,
  "cash_impact": false,
  "active": true
}
```

Regras:

1. Não somar o benefício às receitas em caixa.
2. Não alterar saldo bancário, livre após reserva ou capacidade direta de quitar dívidas.
3. Exibir o benefício como recurso restrito e como parte dos recursos econômicos totais.
4. Quando houver extrato do cartão, registrar créditos e gastos do benefício em uma carteira própria.
5. Se faltar o dia de crédito ou o comprovante, manter a premissa identificada como pendente de confirmação.

## Estimativa do 13º

Antes da confirmação do empregador:

1. calcular os avos prováveis a partir da admissão e da permanência esperada;
2. aplicar uma estimativa líquida conservadora;
3. classificar a entrada como baixa confiança;
4. distribuir as parcelas nas datas estimadas;
5. substituir a estimativa pelo valor real quando o pagamento ocorrer.

Nunca projetar automaticamente um salário líquido integral como 13º quando o vínculo começou durante o ano.

## Atualização de saldo

Um saldo sempre precisa de data:

```json
{
  "account": "itau",
  "balance": 850.00,
  "as_of": "2026-08-05T18:00:00-03:00"
}
```

Depois da atualização, projetar somente eventos pendentes posteriores à data-base. Eventos vencidos e não pagos continuam pendentes.

## Estados recomendados

### Lançamento

```text
previsto -> realizado
previsto -> cancelado
```

### Parcela

```text
prevista -> vencida -> paga
prevista -> paga
prevista -> renegociada
```

### Dívida

```text
ativa -> negociando -> renegociada -> quitada
ativa -> quitada
```

### Proposta

```text
disponível -> aceita
disponível -> recusada
disponível -> expirada
```

## Prevenção de duplicidades

- Usar `idempotency_key` em cada comando externo.
- Guardar ID da mensagem do Telegram ou WhatsApp.
- Não inserir novamente uma transação importada pelo Open Finance.
- Verificar data, valor, conta e identificador bancário.
- Preservar histórico de correções; evitar exclusão silenciosa.
