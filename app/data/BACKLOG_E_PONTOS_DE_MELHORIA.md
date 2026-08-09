# Backlog e pontos de melhoria

## Situação atual

A planilha já possui:

- cadastro de lançamentos;
- contas e conciliação;
- dívidas e propostas;
- parcelamentos compactos;
- recorrências;
- eventos avulsos;
- projeção acumulada;
- orçamento variável;
- reserva mínima;
- cenários de controle e ataque;
- indicadores de dívida reconhecida, dívida ampliada e quitação com descontos máximos;
- indicadores de receita por confiança, receita total, saídas e resultado líquido;
- benefício restrito separado do caixa e recursos econômicos totais;
- janelas mensal, trimestral, semestral, anual e personalizada;
- resumo por janela com salários, entradas, saídas, resultado, saldo final e menor saldo;
- separação entre horizonte analisado e validade da renda projetada;
- painel financeiro.

## Limitações conhecidas

### Qualidade e completude dos dados

- A conciliação do Itaú ainda indica lançamentos ou saldo inicial incompletos.
- O histórico de julho é incompleto e influencia as premissas de gastos.
- O 13º usa uma estimativa conservadora de 8/12 avos e pode diferir do cálculo do empregador.
- O vale-alimentação de R$ 849 ainda precisa de extrato e dia de crédito para confirmação.
- O salário está projetado somente até a data informada.
- Dívidas sem data não reduzem automaticamente um mês da projeção.
- O cenário de quitação com descontos depende dos valores finais das ofertas; economia máxima informada não é garantia de contratação.
- Receitas de baixa confiança, como o 13º estimado, ainda dependem de confirmação de valor e data.

### Automação

- O pagamento de uma parcela ainda exige atualizar `Parcelas pagas`.
- A correspondência entre recorrência prevista e lançamento realizado depende do ID.
- Negociações aceitas ainda precisam ser transformadas manualmente em acordo.
- Não existe importação bancária automática.
- Não existe trilha de auditoria detalhada dentro da planilha.

### Escala

- A base mensal da planilha está limitada aos meses existentes em `Projecao`; a janela personalizada é truncada no último mês disponível.
- O Excel não é apropriado como banco concorrente multiusuário.
- Fórmulas extensas dificultariam evolução; regras devem migrar para serviços de domínio.

## Melhorias prioritárias da planilha

1. Finalizar a conciliação bancária.
2. Confirmar premissas de gastos essenciais e não essenciais.
3. Criar identificadores estáveis para todas as entidades.
4. Automatizar a baixa de parcela pelo ID do lançamento.
5. Registrar data-base e versão da projeção.
6. Adicionar comparação previsto versus realizado.
7. Adicionar alerta para compromisso sem plano de pagamento.
8. Documentar claramente quais campos são editáveis.
9. Criar carteira própria para créditos, saldo e gastos de benefícios restritos.
10. Substituir o 13º estimado pelo cálculo ou pagamento confirmado do empregador.
11. Permitir que a aplicação gere projeções de qualquer duração sem aumentar o tamanho do Excel.

## Roadmap da aplicação

### Fase 1 — domínio e testes

- Definir entidades e estados.
- Criar casos de teste com os exemplos reais da planilha.
- Implementar regras de transferência, parcelamento e renegociação.
- Testar prevenção de duplicidades.

### Fase 2 — FastAPI e PostgreSQL

- Contas, categorias e saldos.
- Lançamentos e transferências.
- Dívidas, acordos e parcelamentos.
- Recorrências.
- Motor mensal de projeção.
- Conciliação.

### Fase 3 — interface

- Painel React.
- Formulários rápidos.
- Calendário financeiro.
- Explicação das variações.
- Simulador de decisão.

### Fase 4 — conversacional

- Telegram.
- WhatsApp.
- Rascunho e confirmação.
- Correção de comando.
- Lembretes e revisão semanal.

### Fase 5 — análise

- Power BI.
- Precisão da previsão.
- Curva de redução de dívidas.
- Taxa de poupança.
- Dependência da renda.
- Alertas de risco.
- Recomendações explicáveis.

### Fase 6 — SaaS e Open Finance

- Multiusuário.
- Autenticação e autorização.
- Isolamento de dados.
- Consentimentos.
- Importação automática.
- Conciliação assistida.
- Auditoria e LGPD.

## Métricas de saúde financeira

- saldo atual;
- saldo final projetado;
- livre após reserva;
- menor saldo futuro;
- taxa de poupança;
- receitas previstas por nível de confiança;
- benefícios restritos previstos;
- recursos econômicos totais separados do caixa;
- receita total estimada;
- saídas e reservas previstas;
- resultado líquido estimado;
- percentual da renda comprometida;
- dívida total;
- dívida reconhecida;
- dívida ampliada pelos saldos originais das ofertas pendentes;
- cenário de quitação com descontos máximos;
- dívida vencida;
- meses para quitação;
- gastos essenciais e não essenciais;
- diferença previsto versus realizado;
- cobertura de compromissos;
- concentração de vencimentos;
- dependência de renda futura;
- patrimônio financeiro líquido.

## Métricas de produto

- tempo para registrar uma movimentação;
- percentual de comandos confirmados sem correção;
- duplicidades evitadas;
- transações conciliadas automaticamente;
- usuários que fazem revisão semanal;
- redução de gastos não essenciais;
- redução da dívida após 30, 90 e 180 dias;
- melhoria da precisão das projeções.

## Princípio de produto

A inserção deve ser simples e rápida. A análise deve ser profunda, explicável e orientada a decisão.

O sistema não deve apenas mostrar números; deve explicar:

- o que mudou;
- por que mudou;
- qual decisão causou o efeito;
- quais compromissos estão em risco;
- quais opções o usuário possui;
- como cada opção altera o futuro.
