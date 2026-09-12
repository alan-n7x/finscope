# Guia para agentes — projeto financeiro pessoal

## Objetivo

Este diretório contém o protótipo de um sistema de inteligência financeira pessoal. A planilha não é apenas um registro de gastos: ela separa fatos realizados, compromissos, premissas e projeções para apoiar decisões e servir como referência funcional para uma aplicação futura.

Antes de alterar qualquer coisa, leia:

1. `README_FINANCEIRO.md`
2. `FLUXOS_DE_INSERCAO.md`
3. `MODELO_DE_DADOS_E_INTEGRACOES.md`
4. `PROMPT_INTERPRETADOR_FINANCEIRO.md`
5. `BACKLOG_E_PONTOS_DE_MELHORIA.md`

## Arquivo oficial e link simbólico

- Arquivo real: `<SUA_PASTA>/OneDrive/Documentos/Financeiro/controle_financeiro.xlsx`
- Caminho usado pela aplicação: `<SEU_PROJETO>/finscope/app/data/database.xlsx`
- `database.xlsx` é um link simbólico para o arquivo real.

Regras obrigatórias:

- Preservar o link simbólico; não substituí-lo por uma cópia comum.
- Confirmar o destino do link antes e depois de qualquer edição.
- Se precisar criar temporários, usar somente:
  `<SEU_PROJETO>/finscope/app/data/.codex_spreadsheet_tmp`
- Remover temporários ao terminar.
- Não criar arquivos `.ndjson`, previews ou scripts permanentes ao lado do Excel.
- Não sobrescrever mudanças do usuário sem antes inspecionar o estado atual.

## Arquitetura da planilha

### Entradas do usuário

- `Lancamentos`: fatos financeiros realizados ou previstos manualmente.
- `Contas`: saldos bancários e data de atualização.
- `Dividas`: obrigações e saldos totais.
- `Parcelamentos`: uma linha por plano parcelado.
- `Recorrentes`: uma linha por receita, despesa ou benefício restrito recorrente.
- `Fluxo Futuro`: somente eventos avulsos, sem repetição mensal.
- `Propostas`: ofertas ainda não aceitas.
- `Premissas`: salário, orçamento, reserva e demais hipóteses editáveis.

### Cálculo e controle

- `Projecao`: fluxo mensal acumulado.
- `Conciliacao`: compara saldo calculado com saldo informado.
- `Cenarios`: compara padrões de gasto, capacidade de ataque às dívidas e janelas móveis de previsão.
- `Orcamento`: limites e realizado por categoria.

### Saídas

- `Painel`: visão executiva do mês e resumo da janela de previsão selecionada.
- `Metas`: objetivos financeiros.

## Regras de negócio críticas

1. Uma transferência entre contas próprias tem impacto financeiro total zero.
2. Uma proposta não aceita não altera dívida, caixa ou projeção.
3. Um parcelamento é cadastrado uma vez; não cadastrar manualmente todas as parcelas no fluxo.
4. O pagamento de uma parcela gera um lançamento e atualiza `Parcelas pagas`.
5. Uma dívida sem data afeta endividamento, mas não um mês específico do fluxo de caixa.
6. Uma renegociação preserva a dívida original como histórico e cria um novo acordo.
7. O saldo é sempre uma fotografia com data de referência.
8. A projeção deve considerar o saldo na data-base mais somente eventos ainda pendentes.
9. Nunca contar simultaneamente o valor total de uma compra parcelada e todas as suas parcelas no caixa.
10. Valores calculados pertencem às abas de cálculo; não devem ser inseridos manualmente.
11. Benefícios restritos, como vale-alimentação, não compõem saldo bancário nem capacidade direta de pagar dívidas.
12. Estimativas de 13º devem considerar os avos prováveis, permanecer com baixa confiança e ser substituídas pelo valor real quando confirmado.
13. Relatórios de endividamento devem separar dívida reconhecida, dívida ampliada com ofertas pendentes e cenário hipotético de quitação com descontos.
14. Relatórios de renda devem separar receita total, confiança das entradas, saídas e reservas, resultado líquido e saldo final; receita não é sinônimo de dinheiro livre.
15. A janela mensal, trimestral, semestral, anual ou personalizada não altera a validade da renda; salário não pode ser repetido após `Renda atual prevista até`.

## Procedimento antes de editar

1. Resolver e validar o link simbólico.
2. Inspecionar valores, fórmulas, abas e intervalos afetados.
3. Renderizar visualmente as abas relevantes.
4. Rastrear precedentes dos indicadores importantes.
5. Fazer a menor alteração consistente possível.
6. Verificar erros de fórmula e reconciliações.
7. Renderizar novamente.
8. Atualizar esta documentação se o modelo de dados ou as regras mudarem.

## Convenções para integrações futuras

- IDs devem ser estáveis e únicos.
- Valores monetários devem usar decimal, nunca ponto flutuante binário na API ou banco.
- Datas devem usar ISO 8601.
- Toda inserção por linguagem natural deve gerar um rascunho e exigir confirmação.
- Operações devem ser idempotentes para evitar duplicidade em WhatsApp, Telegram ou Open Finance.
- PostgreSQL será a fonte oficial quando a aplicação estiver operacional.
- O Excel deverá continuar disponível como importação, exportação e relatório portátil.
